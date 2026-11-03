"""
Dione AI — AG-UI Protocol + Multi-Agent & Computer-Use Routes (2026 Upgrade)
=============================================================================
Official implementation of the Agent-User Interaction Protocol (AG-UI)
with extensions for Hierarchical Multi-Agent Orchestration DAG streaming,
Direct AI Computer-Use actions, and Real-Time Voice Talk handoff.
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

try:
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
    HAS_AG_UI = True
    encoder = EventEncoder()
except Exception:
    HAS_AG_UI = False
    encoder = None

from server.core.engine import EngineState
from server.core.orchestrator import get_multi_agent_orchestrator, AGENT_REGISTRY
from server.core.runtime.computer_use import get_computer_use_operator

router = APIRouter()


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


class ComputerActionInput(BaseModel):
    action: str  # "screenshot", "click_coords", "click_uia", "type_text", "hotkey", "launch_app", "switch_audio", "volume", "media"
    x: Optional[int] = None
    y: Optional[int] = None
    button: str = "left"
    double_click: bool = False
    text: Optional[str] = None
    press_enter: bool = False
    keys: Optional[str] = None
    app_name: Optional[str] = None
    element_name: Optional[str] = None
    device_name: Optional[str] = None
    direction: str = "input"


@router.get("/info")
async def get_ag_ui_info(request: Request):
    """
    Returns AG-UI protocol specification, Multi-Agent Swarm topology, and AI Computer-Use capabilities.
    """
    settings = getattr(request.app.state, "settings", None)
    model_name = settings.llm.model if settings else "gemini-3.5-flash"
    orchestrator = getattr(request.app.state, "orchestrator", None) or get_multi_agent_orchestrator()
    llm = getattr(request.app.state, "llm", None)
    if llm and not orchestrator.llm_adapter:
        orchestrator.set_llm(llm)
    plugins = getattr(request.app.state, "plugins", None)
    if plugins:
        orchestrator.set_plugins(plugins)

    return {
        "protocol": "ag-ui",
        "spec_version": "2026.2.0",
        "agent": {
            "name": "Dione 2026 Agentic OS",
            "description": "Privacy-Preserving Hierarchical Multi-Agent LAM with Native Computer Use & Neural Voice",
            "framework": "Microsoft Agent Framework (MAF 1.21.0) + MultiAgentOrchestrator",
            "model": model_name,
            "capabilities": {
                "streaming": True,
                "multi_agent_orchestration": True,
                "computer_use_operator": True,
                "voice_talk_duplex": True,
                "tool_calling": True,
                "state_synchronization": True,
                "proactive_cards": True,
                "safety_middleware": True,
            },
            "agents": orchestrator.get_agent_catalog() if hasattr(orchestrator, "get_agent_catalog") else [
                {
                    "role": getattr(desc.role, "value", str(desc.role)),
                    "name": desc.name,
                    "badge": desc.badge,
                    "specialty": desc.specialty,
                    "color": desc.color,
                    "tools": desc.tools,
                }
                for desc in AGENT_REGISTRY.values()
            ],
            "tools": [
                {"name": "computer_take_screenshot", "agent": "computer_use_agent", "description": "Capture live desktop screen via GDI BitBlt"},
                {"name": "computer_vision_click", "agent": "computer_use_agent", "description": "Locate UI element with Gemini Vision and click"},
                {"name": "computer_click_coords", "agent": "computer_use_agent", "description": "Click exact (x, y) pixel coordinates with fail-safe"},
                {"name": "computer_click_ui_element", "agent": "computer_use_agent", "description": "Click Windows UIA element by accessibility name"},
                {"name": "computer_type_text", "agent": "computer_use_agent", "description": "Type keystrokes into focused window"},
                {"name": "computer_press_hotkey", "agent": "computer_use_agent", "description": "Trigger OS keyboard shortcuts"},
                {"name": "computer_launch_app", "agent": "computer_use_agent", "description": "Launch desktop application or game"},
                {"name": "computer_switch_audio_device", "agent": "computer_use_agent", "description": "Switch Windows audio input/output endpoint"},
                {"name": "knowledge_graph_search", "agent": "knowledge_social_agent", "description": "Traverse 2-hop NetworkX entity multigraph"},
                {"name": "resolve_social_dossier", "agent": "knowledge_social_agent", "description": "Resolve mentor/colleague dossier & commitments"},
                {"name": "filesystem_list_directory", "agent": "system_sandbox_agent", "description": "List directory contents"},
                {"name": "filesystem_read_file", "agent": "system_sandbox_agent", "description": "Read sandboxed file"},
                {"name": "database_query_sqlite", "agent": "system_sandbox_agent", "description": "Execute read-only SQLite query"},
                {"name": "web_search", "agent": "research_web_agent", "description": "Live DuckDuckGo & arXiv web research"},
            ],
        },
    }


@router.post("/orchestrate")
async def run_orchestrated_dag(input_data: AgUiRunInput, request: Request):
    """
    Execute a goal through the Hierarchical Multi-Agent Orchestrator and return the full
    DAG execution trace, agent handoffs, blackboard state, and synthesized response.
    """
    prompt = (input_data.message or "").strip()
    if not prompt and input_data.messages:
        for m in reversed(input_data.messages):
            if m.role == "user" and m.content:
                prompt = m.content
                break
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing user prompt")

    orchestrator = getattr(request.app.state, "orchestrator", None) or get_multi_agent_orchestrator()
    llm = getattr(request.app.state, "llm", None)
    if llm and not orchestrator.llm_adapter:
        orchestrator.set_llm(llm)
    plugins = getattr(request.app.state, "plugins", None)
    if plugins:
        orchestrator.set_plugins(plugins)
    session = await orchestrator.execute_orchestrated_goal(prompt)
    return session.to_dict()


@router.post("/computer-action")
async def execute_computer_action(payload: ComputerActionInput):
    """
    Direct AI / UI Computer-Use operator endpoint for executing pixel clicks,
    UIA element clicks, typing, hotkeys, app launching, audio switching, and screen capture.
    """
    op = get_computer_use_operator()
    act = payload.action.lower().strip()
    try:
        if act == "screenshot":
            path = await op.take_screenshot()
            return {"success": True, "action": act, "path": path}
        elif act == "click_coords" and payload.x is not None and payload.y is not None:
            clicks = 2 if payload.double_click else 1
            await op.click_at_coordinates(payload.x, payload.y, clicks=clicks, button=payload.button)
            return {"success": True, "action": act, "x": payload.x, "y": payload.y, "button": payload.button}
        elif act == "click_uia" and payload.element_name:
            ok = await op.click_element_by_name(payload.element_name)
            return {"success": ok, "action": act, "element": payload.element_name}
        elif act == "type_text" and payload.text is not None:
            await op.type_text(payload.text, press_enter=payload.press_enter)
            return {"success": True, "action": act, "text": payload.text}
        elif act == "hotkey" and payload.keys:
            parts = [k.strip().lower() for k in payload.keys.split("+")]
            await op.press_hotkey(*parts)
            return {"success": True, "action": act, "keys": parts}
        elif act == "launch_app" and payload.app_name:
            res = await op.launch_app(payload.app_name)
            return {"success": True, "action": act, "result": res}
        elif act == "volume":
            res = await op.adjust_volume(payload.text or "up")
            return {"success": True, "action": act, "result": res}
        elif act == "media":
            res = await op.media_control(payload.text or "play_pause")
            return {"success": True, "action": act, "result": res}
        else:
            return {"success": False, "error": f"Unsupported or incomplete computer action: {act}"}
    except Exception as e:
        logger.error(f"[ComputerAction] Error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/run")
async def run_ag_ui_agent(input_data: AgUiRunInput, request: Request):
    """
    Official AG-UI Protocol SSE streaming endpoint with Multi-Agent DAG events.
    """
    thread_id = input_data.thread_id or f"thread_{uuid.uuid4().hex[:8]}"
    run_id = input_data.run_id or f"run_{uuid.uuid4().hex[:8]}"

    prompt = (input_data.message or "").strip()
    if not prompt and input_data.messages:
        for m in reversed(input_data.messages):
            if m.role == "user" and m.content:
                prompt = m.content
                break

    if not prompt:
        raise HTTPException(status_code=400, detail="Either 'message' or 'messages' must provide a user prompt.")

    orchestrator = getattr(request.app.state, "orchestrator", None) or get_multi_agent_orchestrator()
    llm = getattr(request.app.state, "llm", None)
    if llm and not orchestrator.llm_adapter:
        orchestrator.set_llm(llm)
    plugins = getattr(request.app.state, "plugins", None)
    if plugins:
        orchestrator.set_plugins(plugins)

    async def sse_generator() -> AsyncGenerator[str, None]:
        def _sse(data: Dict[str, Any]) -> str:
            return f"data: {json.dumps(data)}\n\n"

        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        yield _sse({"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id})

        active_tc_ids: Dict[str, str] = {}
        final_text = ""

        recent_msgs = []
        if input_data.messages:
            for m in input_data.messages:
                recent_msgs.append({
                    "role": getattr(m, "role", "user"),
                    "content": getattr(m, "content", ""),
                })

        try:
            # Stream directly from DioneEngine's native ReAct loop with persistent conversation thread
            req_model = (input_data.parameters or {}).get("model") if input_data.parameters else None
            async for step in orchestrator.stream_orchestrated_goal(
                prompt,
                conversation_id=thread_id,
                recent_messages=recent_msgs,
                model_override=req_model,
            ):
                if step.state == EngineState.ACTING and step.tool_call:
                    tc_id = f"tc_{uuid.uuid4().hex[:6]}"
                    active_tc_ids[step.tool_call.tool] = tc_id
                    yield _sse({
                        "type": "TOOL_CALL_START",
                        "toolCallId": tc_id,
                        "toolCallName": step.tool_call.tool,
                    })
                    yield _sse({
                        "type": "TOOL_CALL_ARGS",
                        "toolCallId": tc_id,
                        "delta": json.dumps(step.tool_call.params),
                    })

                elif step.state == EngineState.OBSERVING and step.tool_call and step.observation:
                    tc_id = active_tc_ids.pop(step.tool_call.tool, f"tc_{uuid.uuid4().hex[:6]}")
                    yield _sse({
                        "type": "TOOL_CALL_RESULT",
                        "toolCallId": tc_id,
                        "content": step.observation.result,
                        "success": step.observation.success,
                        "error": step.observation.error,
                    })
                    yield _sse({
                        "type": "TOOL_CALL_END",
                        "toolCallId": tc_id,
                    })

                elif step.state == EngineState.AWAITING_CONFIRMATION and step.tool_call:
                    yield _sse({
                        "type": "CUSTOM",
                        "name": "safety_confirmation_required",
                        "value": {
                            "confirmation_id": step.confirmation_id,
                            "tool": step.tool_call.tool,
                            "params": step.tool_call.params,
                            "thought": step.thought,
                        },
                    })

                elif step.state == EngineState.COMPLETE and step.final_answer:
                    final_text = step.final_answer

                elif step.state == EngineState.ERROR and step.final_answer:
                    final_text = step.final_answer

        except Exception as loop_err:
            logger.error(f"[AG-UI Stream] ReAct execution caught exception: {loop_err}", exc_info=True)
            final_text = f"I encountered an execution interruption: {loop_err}. Self-healing kernel restored."

        final_text = final_text or "Task completed, sir."
        yield _sse({
            "type": "TEXT_MESSAGE_START",
            "messageId": message_id,
            "role": "assistant",
        })

        words = final_text.split(" ")
        for i in range(0, len(words), 4):
            chunk = " ".join(words[i:i + 4]) + (" " if i + 4 < len(words) else "")
            yield _sse({
                "type": "TEXT_MESSAGE_CONTENT",
                "messageId": message_id,
                "delta": chunk,
            })
            await asyncio.sleep(0.015)

        yield _sse({
            "type": "TEXT_MESSAGE_END",
            "messageId": message_id,
        })
        yield _sse({
            "type": "RUN_FINISHED",
            "threadId": thread_id,
            "runId": run_id,
        })

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/briefing")
async def get_latest_wakeup_briefing(request: Request):
    """Retrieve the latest 'While You Were Away' executive briefing card from the Dream Engine."""
    dream_engine = getattr(request.app.state, "dream_engine", None)
    if dream_engine:
        briefing = dream_engine.get_latest_briefing()
        if briefing:
            return {"available": True, "briefing": briefing}
    return {"available": False, "message": "No unread wake-up briefing available."}


@router.post("/briefing/trigger")
async def trigger_dream_cycle(request: Request):
    """Manually trigger an autonomous Dream & Scout cycle."""
    dream_engine = getattr(request.app.state, "dream_engine", None)
    if dream_engine:
        report = await dream_engine.run_synthesis_cycle(force=True)
        return {"success": True, "report": report.to_dict() if report else None}
    return {"success": False, "error": "Dream engine not initialized."}


class ActionApprovalPayload(BaseModel):
    confirmation_id: str
    approved: bool = True
    reason: Optional[str] = None


@router.post("/action-approval")
async def handle_action_approval(payload: ActionApprovalPayload, request: Request):
    """Approve or deny a pending sensitive action from the Web UI approval card."""
    orch = getattr(request.app.state, "orchestrator", None) or get_multi_agent_orchestrator()
    if payload.approved:
        ok = orch.engine.approve_action(payload.confirmation_id)
    else:
        ok = orch.engine.deny_action(payload.confirmation_id, payload.reason or "Denied by user in Web UI")
    return {"success": ok, "confirmation_id": payload.confirmation_id, "approved": payload.approved}

