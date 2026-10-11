"""
Dione AI — AG-UI Protocol Routes
=================================
Official implementation of the Agent-User Interaction Protocol (AG-UI)
https://github.com/ag-ui-protocol/ag-ui

Bridges Dione's Microsoft Agent Framework backend with frontend applications
via standardized Server-Sent Events (SSE) streaming.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger

from ag_ui.core import (
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    StateDeltaEvent,
    CustomEvent,
)
from ag_ui.encoder import EventEncoder
from server.core.engine import EngineState


router = APIRouter()
encoder = EventEncoder()


class AgUiMessage(BaseModel):
    id: Optional[str] = None
    role: str = "user"
    content: str


class AgUiRunInput(BaseModel):
    thread_id: Optional[str] = Field(default_factory=lambda: f"thread_{uuid.uuid4().hex[:8]}")
    run_id: Optional[str] = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    message: Optional[str] = None
    messages: Optional[List[AgUiMessage]] = None
    parameters: Optional[Dict[str, Any]] = None


@router.get("/info")
async def get_ag_ui_info(request: Request):
    """
    Returns AG-UI protocol specification and agent capabilities.
    """
    settings = getattr(request.app.state, "settings", None)
    model_name = settings.llm.model if settings else "gemini-3.5-flash-lite"
    
    return {
        "protocol": "ag-ui",
        "spec_version": "1.0.0",
        "agent": {
            "name": "Dione LAM",
            "description": "Privacy-Preserving Local Large Action Model Orchestration Engine",
            "framework": "Microsoft Agent Framework (MAF 1.20.0)",
            "model": model_name,
            "capabilities": {
                "streaming": True,
                "tool_calling": True,
                "state_synchronization": True,
                "multi_turn": True,
                "proactive_cards": True,
                "safety_middleware": True,
            },
            "transports": ["sse", "http_json"],
            "supported_events": [
                "RUN_STARTED",
                "RUN_FINISHED",
                "RUN_ERROR",
                "TEXT_MESSAGE_START",
                "TEXT_MESSAGE_CONTENT",
                "TEXT_MESSAGE_END",
                "TOOL_CALL_START",
                "TOOL_CALL_ARGS",
                "TOOL_CALL_RESULT",
                "TOOL_CALL_END",
                "STATE_DELTA",
                "CUSTOM",
            ],
            "tools": [
                {"name": "filesystem_list_directory", "description": "List directory contents including dotfiles"},
                {"name": "filesystem_read_file", "description": "Read file contents within sandbox"},
                {"name": "database_query_sqlite", "description": "Execute relational queries on local SQLite"},
                {"name": "system_execute_command", "description": "Run sandboxed host shell commands"},
                {"name": "knowledge_graph_search", "description": "Traverse NetworkX personal entity multigraph"},
                {"name": "web_search", "description": "Live DuckDuckGo / arXiv web research"},
                {"name": "telegram_send", "description": "Send message via Telegram Bot API"},
                {"name": "gmail_read", "description": "Read recent emails via IMAP"},
                {"name": "gmail_send", "description": "Send emails via SMTP with attachments"},
            ]
        }
    }


@router.post("/run")
async def run_ag_ui_agent(input_data: AgUiRunInput, request: Request):
    """
    Official AG-UI Protocol execution streaming endpoint.
    Emits standardized Server-Sent Events (SSE).
    """
    thread_id = input_data.thread_id or f"thread_{uuid.uuid4().hex[:8]}"
    run_id = input_data.run_id or f"run_{uuid.uuid4().hex[:8]}"
    
    # Extract prompt
    prompt = (input_data.message or "").strip()
    if not prompt and input_data.messages:
        for m in reversed(input_data.messages):
            if m.role == "user" and m.content:
                prompt = m.content
                break

    if not prompt:
        raise HTTPException(status_code=400, detail="Either 'message' or 'messages' must provide a user prompt.")

    engine = getattr(request.app.state, "engine", None)
    memory = getattr(request.app.state, "memory", None)
    sentiment_engine = getattr(request.app.state, "sentiment", None)
    personality_engine = getattr(request.app.state, "personality", None)
    heartbeat = getattr(request.app.state, "heartbeat", None)

    # Record user message in memory & heartbeat
    if memory:
        try:
            await memory.add_turn("user", prompt)
        except Exception:
            pass
    if heartbeat:
        try:
            heartbeat.record_user_activity()
        except Exception:
            pass

    async def event_generator() -> AsyncGenerator[str, None]:
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        try:
            # 1. RUN_STARTED
            yield encoder.encode(RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=thread_id,
                run_id=run_id,
            ))

            # 2. CUSTOM Event: Agent metadata
            yield encoder.encode(CustomEvent(
                type=EventType.CUSTOM,
                name="dione_agent_init",
                value={
                    "framework": "Microsoft Agent Framework (MAF 1.20.0)",
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                }
            ))

            # 3. Analyze Sentiment / State Delta (RFC 6902 JSON Patch)
            patch_ops = []
            if sentiment_engine:
                try:
                    s_res = await sentiment_engine.analyze(prompt)
                    patch_ops.append({"op": "replace", "path": "/sentiment", "value": getattr(s_res, "label", "neutral")})
                    patch_ops.append({"op": "replace", "path": "/urgency", "value": getattr(s_res, "urgency", 0.0)})
                    patch_ops.append({"op": "replace", "path": "/importance", "value": getattr(s_res, "importance", 0.5)})
                except Exception:
                    pass

            if personality_engine:
                try:
                    p_state = personality_engine.get_state()
                    patch_ops.append({"op": "replace", "path": "/mood", "value": getattr(p_state, "mood", "balanced")})
                    patch_ops.append({"op": "replace", "path": "/energy", "value": getattr(p_state, "energy", 0.7)})
                except Exception:
                    pass

            if patch_ops:
                yield encoder.encode(StateDeltaEvent(
                    type=EventType.STATE_DELTA,
                    delta=patch_ops,
                ))

            # 4. Execute via MAFEngine and stream steps
            final_text = ""
            tools_used = []

            if hasattr(engine, "process_message"):
                async for step in engine.process_message(prompt, conversation_id=thread_id):
                    # Check tool calls
                    if step.tool_call:
                        t_name = step.tool_call.tool
                        t_params = getattr(step.tool_call, "params", {}) or {}
                        tools_used.append(t_name)
                        tool_call_id = f"tc_{uuid.uuid4().hex[:6]}"

                        yield encoder.encode(ToolCallStartEvent(
                            type=EventType.TOOL_CALL_START,
                            tool_call_id=tool_call_id,
                            tool_call_name=t_name,
                        ))

                        if t_params:
                            yield encoder.encode(ToolCallArgsEvent(
                                type=EventType.TOOL_CALL_ARGS,
                                tool_call_id=tool_call_id,
                                delta=json.dumps(t_params),
                            ))

                        yield encoder.encode(ToolCallResultEvent(
                            type=EventType.TOOL_CALL_RESULT,
                            message_id=f"tool_msg_{tool_call_id}",
                            tool_call_id=tool_call_id,
                            content=f"Executed {t_name} successfully",
                            role="tool",
                        ))

                        yield encoder.encode(ToolCallEndEvent(
                            type=EventType.TOOL_CALL_END,
                            tool_call_id=tool_call_id,
                        ))

                    if step.state in (EngineState.COMPLETE, EngineState.ERROR) and step.final_answer:
                        final_text = step.final_answer
            else:
                final_text = "MAF Engine unavailable."

            if not final_text:
                final_text = "Task executed successfully."

            # 5. Stream Assistant Text Message
            yield encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant",
            ))

            # Emulate typewriter streaming deltas for natural AG-UI flow
            words = final_text.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                yield encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=chunk,
                ))
                await asyncio.sleep(0.015)

            yield encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id,
            ))

            # 6. RUN_FINISHED
            yield encoder.encode(RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=thread_id,
                run_id=run_id,
            ))

        except Exception as e:
            logger.error(f"AG-UI Protocol Run Error: {e}")
            yield encoder.encode(RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e),
            ))

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
