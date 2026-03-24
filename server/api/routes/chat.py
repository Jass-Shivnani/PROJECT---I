"""
Dione AI — Chat Routes

WebSocket and REST endpoints for chat communication.
The WebSocket provides real-time streaming; REST provides
a simpler request/response for one-off messages.
"""

import json
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from loguru import logger

from server.core.engine import EngineState


router = APIRouter()


# ------------------------------------------------------------------
# REST endpoint: Simple message → response
# ------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sentiment: Optional[dict] = None
    tools_used: list[str] = []
    latency_ms: float = 0.0
    ui: Optional[dict] = None    # Dynamic UI directives
    mood: Optional[dict] = None  # Dione's current mood


@router.post("/chat", response_model=ChatResponse)
async def chat_message(req: ChatRequest, request: Request):
    """
    Send a message to Dione and get a complete response.

    This is the simpler REST endpoint — for real-time streaming,
    use the WebSocket at /api/chat/ws instead.
    """
    engine = request.app.state.engine
    memory = request.app.state.memory

    start = time.monotonic()

    # Store user message in memory
    await memory.add_turn("user", req.message)

    # Record user activity for adaptive heartbeat
    if hasattr(request.app.state, "heartbeat"):
        request.app.state.heartbeat.record_user_activity()

    # Process through the ReAct engine
    final_response = ""
    tools_used = []
    sentiment_data = None

    async for step in engine.process_message(req.message):
        # EngineStep dataclass: .state, .final_answer, .tool_call, .observation, .thought
        if step.state in (EngineState.COMPLETE, EngineState.ERROR) and step.final_answer:
            final_response = step.final_answer
        elif step.tool_call:
            tools_used.append(step.tool_call.tool)
        # Observation steps are internal — skip for REST response

    # Note: Assistant response is already stored by engine.process_message()

    latency = (time.monotonic() - start) * 1000

    # Generate UI directives — the AI decides how the app looks
    ui_directives = engine.get_ui_directives(final_response, tools_used)

    # Get current mood
    mood_data = None
    if hasattr(request.app.state, "personality"):
        mood_data = request.app.state.personality.mood.to_dict()

    # Save profile & personality state periodically
    if hasattr(request.app.state, "profile"):
        request.app.state.profile.save()
    if hasattr(request.app.state, "personality"):
        request.app.state.personality.save()

    return ChatResponse(
        response=final_response or "I wasn't able to produce a response. Please try again.",
        conversation_id=req.conversation_id or "default",
        sentiment=sentiment_data,
        tools_used=tools_used,
        latency_ms=round(latency, 2),
        ui=ui_directives,
        mood=mood_data,
    )


@router.post("/chat/reset")
async def reset_conversation(request: Request):
    """Reset the conversation history."""
    engine = request.app.state.engine
    engine.reset_conversation()
    return {"status": "ok", "message": "Conversation reset"}


# ------------------------------------------------------------------
# WebSocket endpoint: Real-time streaming chat
# ------------------------------------------------------------------

@router.websocket("/chat/ws")
async def chat_websocket(websocket: WebSocket):
    """
    Real-time WebSocket chat with Dione.

    Protocol:
    - Client sends: {"type": "message", "content": "..."}
    - Server sends: {"type": "token", "content": "..."} (streaming)
    - Server sends: {"type": "tool_call", "tool": "...", "args": {...}}
    - Server sends: {"type": "tool_result", "tool": "...", "result": "..."}
    - Server sends: {"type": "sentiment", "data": {...}}
    - Server sends: {"type": "done", "full_response": "..."}
    - Server sends: {"type": "error", "message": "..."}
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    engine = websocket.app.state.engine
    memory = websocket.app.state.memory

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            msg_type = data.get("type", "message")
            content = data.get("content", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type != "message" or not content.strip():
                continue

            # Store user message
            await memory.add_turn("user", content)

            # Record user activity for adaptive heartbeat
            if hasattr(websocket.app.state, "heartbeat"):
                websocket.app.state.heartbeat.record_user_activity()

            # Process through engine and stream EngineStep events
            full_response = ""
            try:
                async for step in engine.process_message(content):
                    # step is an EngineStep dataclass

                    if step.thought:
                        await websocket.send_json({
                            "type": "thought",
                            "content": step.thought,
                        })

                    if step.tool_call:
                        await websocket.send_json({
                            "type": "tool_call",
                            "tool": step.tool_call.tool,
                            "args": step.tool_call.params,
                        })

                    if step.observation:
                        await websocket.send_json({
                            "type": "tool_result",
                            "tool": step.observation.tool,
                            "result": step.observation.result,
                            "success": step.observation.success,
                        })

                    if step.state == EngineState.AWAITING_CONFIRMATION and step.tool_call:
                        await websocket.send_json({
                            "type": "confirmation_needed",
                            "tool": step.tool_call.tool,
                            "args": step.tool_call.params,
                            "message": f"Allow {step.tool_call.tool}?",
                        })
                        confirm_raw = await websocket.receive_text()
                        confirm_data = json.loads(confirm_raw)
                        if confirm_data.get("type") == "confirm":
                            # TODO: Resume engine with confirmation
                            pass

                    if step.state == EngineState.COMPLETE and step.final_answer:
                        full_response = step.final_answer

                # Send final complete response
                await websocket.send_json({
                    "type": "done",
                    "full_response": full_response,
                })

                # Note: Assistant response is already stored by engine.process_message()

            except Exception as e:
                logger.error(f"Engine error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# ------------------------------------------------------------------
# Conversation history
# ------------------------------------------------------------------

@router.get("/chat/history")
async def get_history(request: Request, n: int = 20):
    """Get recent conversation history."""
    memory = request.app.state.memory
    turns = memory.get_recent_turns(n)
    return {
        "turns": [
            {
                "id": t.id,
                "role": t.role,
                "content": t.content,
                "timestamp": t.timestamp,
                "sentiment": t.sentiment,
            }
            for t in turns
        ]
    }
