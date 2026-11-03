"""
Dione AI — Live Audio & Gemini 3.8 Extended Thinking + Backend Engine Bridge
=============================================================================
Full-duplex WebSocket & REST endpoints connecting:
1. Gemini Live Native Audio Frontman (24kHz output / 16kHz input with user-selected Mic).
2. `deep_think_gemini_3_8`: Invokes Gemini 3.8 Flash with Extended Thinking (`ThinkingConfig`)
   when the user asks complex reasoning, math, coding, or architectural questions over voice.
3. `execute_dione_action`: Invokes the backend `DioneEngine` (Computer-Use, Gmail, Calendar,
   Drive, Photos, WhatsApp, Telegram, Slack, Instagram, Web Search, Filesystem) directly from voice!
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile
from typing import List, Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from loguru import logger

from server.llm.gemini_live_orchestrator import get_live_flash_orchestrator
from server.core.runtime.computer_use import list_audio_devices

router = APIRouter()


class AIStudioConfigPayload(BaseModel):
    api_keys: Optional[List[str]] = None
    live_frontman_model: Optional[str] = "gemini-2.5-flash-native-audio-latest"
    reasoning_model: Optional[str] = "gemini-3.8-flash"
    background_flash_model: Optional[str] = "gemini-3.5-flash-lite"
    thinking_budget: Optional[int] = 8192
    voice_name: Optional[str] = "Aoede"


class BackgroundTaskPayload(BaseModel):
    goal: str


@router.get("/devices")
async def get_system_audio_devices():
    """Return available system audio devices from host OS alongside WebRTC browser enumeration."""
    try:
        return list_audio_devices()
    except Exception as e:
        return {"input": [], "output": [], "note": str(e)}


@router.post("/aistudio-config")
async def update_aistudio_config(payload: AIStudioConfigPayload):
    orch = get_live_flash_orchestrator()
    updated = orch.update_config(
        api_keys=payload.api_keys,
        live_model=payload.live_frontman_model,
        reasoning_model=payload.reasoning_model,
        flash_model=payload.background_flash_model,
        thinking_budget=payload.thinking_budget,
        voice_name=payload.voice_name,
    )
    return {"success": True, "config": updated}


@router.get("/aistudio-config")
async def get_aistudio_config():
    orch = get_live_flash_orchestrator()
    return {
        "live_frontman_model": orch.config.live_frontman_model,
        "reasoning_model": orch.config.reasoning_model,
        "background_flash_model": orch.config.background_flash_model,
        "thinking_budget": orch.config.thinking_budget,
        "voice_name": orch.config.voice_name,
        "configured_keys_count": len(orch.key_pool.keys),
        "active_tasks": list(orch.task_results.values()),
    }


@router.post("/spawn-flash-task")
async def spawn_background_flash_task(payload: BackgroundTaskPayload):
    orch = get_live_flash_orchestrator()
    task_id = await orch.spawn_background_task(payload.goal, is_voice_mode=True)
    return {
        "success": True,
        "task_id": task_id,
        "status": "running",
        "delegated_to": orch.config.background_flash_model,
    }


@router.websocket("/live")
async def audio_live_session(websocket: WebSocket):
    """
    Full-Duplex Bidirectional WebSocket endpoint for Gemini Live Voice + Gemini 3.8 Extended Thinking
    + DioneEngine Backend Tool Execution.
    """
    await websocket.accept()
    logger.info("🎤 Gemini Live Voice + Extended Thinking WebSocket connected")
    orch = get_live_flash_orchestrator()

    # Ensure orchestrator has the app's initialized engine & integrations
    if hasattr(websocket.app.state, "engine") and websocket.app.state.engine:
        orch.orchestrator.engine = websocket.app.state.engine

    api_key = (
        orch.key_pool.get_active_key()
        or os.getenv("DIONE_LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )
    if not api_key:
        await websocket.send_json({"type": "error", "message": "No Gemini API key configured in .env"})
        await websocket.close()
        return

    from google import genai
    from google.genai import types

    client = genai.Client(http_options={"api_version": "v1beta"}, api_key=api_key)
    voice_name = websocket.query_params.get("voice") or orch.config.voice_name or "Aoede"

    # Define the 2 bridge tools that connect Gemini Live to Gemini 3.8 Extended Thinking & DioneEngine
    live_tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="execute_dione_action",
                    description=(
                        "Execute any desktop computer-use action (launch app, click button, open browser, play YouTube video, inspect screen), "
                        "local file/system operation, web search, or connected service action (Gmail, Google Calendar, Google Drive, "
                        "Google Photos, WhatsApp, Telegram, Slack, Instagram) via the backend DioneEngine."
                    ),
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "goal": {
                                "type": "STRING",
                                "description": "Complete natural-language instruction of the action or workflow to execute.",
                            }
                        },
                        "required": ["goal"],
                    },
                ),
                types.FunctionDeclaration(
                    name="deep_think_gemini_3_8",
                    description=(
                        "Invoke the backend Gemini 3.8 Flash model with Extended Thinking and Knowledge Graph access "
                        "whenever the user asks a complex reasoning, coding, mathematical, analytical, or multi-step planning question."
                    ),
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "problem": {
                                "type": "STRING",
                                "description": "The complex question or problem requiring extended thinking and deep reasoning.",
                            }
                        },
                        "required": ["problem"],
                    },
                ),
            ]
        )
    ]

    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        tools=live_tools,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(
                text=(
                    "You are Dione, an executive personal AI assistant (Jarvis persona) running on the user's Windows 11 workstation. "
                    "Speak naturally, concisely, and warmly without markdown symbols. "
                    "CRITICAL CAPABILITIES:\n"
                    "1. Whenever the user asks you to DO something on their computer, browser, files, or services "
                    "(e.g. open an app, play a video, click something, check/send email, check calendar, send a WhatsApp/Telegram/Slack message, search the web), "
                    "IMMEDIATELY call `execute_dione_action(goal=...)` and then speak the result.\n"
                    "2. Whenever the user asks a complex question that benefits from deeper reasoning, math, code architecture, or personal knowledge lookup, "
                    "call `deep_think_gemini_3_8(problem=...)` and synthesize its answer naturally."
                )
            )]
        ),
    )

    live_candidates = [
        "models/gemini-3.8-live-extended-thinking",
        "models/gemini-3.8-live",
        orch.config.live_frontman_model,
        "models/gemini-2.5-flash-native-audio-latest",
        "gemini-2.5-flash-native-audio-latest",
    ]
    live_candidates = list(dict.fromkeys([m for m in live_candidates if m]))

    connected_session = None
    last_err = None
    for live_model in live_candidates:
        try:
            cfg_kwargs: dict = {
                "response_modalities": ["AUDIO"],
                "tools": live_tools,
                "media_resolution": "MEDIA_RESOLUTION_MEDIUM",
                "speech_config": types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                ),
                "context_window_compression": types.ContextWindowCompressionConfig(
                    trigger_tokens=104857,
                    sliding_window=types.SlidingWindow(target_tokens=52428),
                ),
                "system_instruction": types.Content(
                    parts=[types.Part.from_text(
                        text=(
                            "You are Dione, an executive personal AI assistant (Jarvis persona) running on the user's Windows 11 workstation. "
                            "Speak naturally, concisely, and warmly without markdown symbols or asterisks. "
                            "CRITICAL CAPABILITIES:\n"
                            "1. Whenever the user asks you to DO something on their computer, browser, files, or services "
                            "(e.g. open an app, play a video, click something, check/send email, check calendar, send a WhatsApp/Telegram/Slack message, search the web), "
                            "IMMEDIATELY call `execute_dione_action(goal=...)` and then speak the result.\n"
                            "2. Whenever the user asks a complex question that benefits from deeper reasoning, math, code architecture, or personal knowledge lookup, "
                            "call `deep_think_gemini_3_8(problem=...)` and synthesize its answer naturally."
                        )
                    )]
                ),
            }
            if "thinking" in live_model.lower():
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="LOW")

            live_cfg = types.LiveConnectConfig(**cfg_kwargs)

            async with client.aio.live.connect(model=live_model, config=live_cfg) as live_session:
                connected_session = True
                await websocket.send_json({
                    "type": "session_ready",
                    "model": live_model,
                    "reasoning_model": orch.config.reasoning_model,
                    "voice": voice_name,
                })

                async def client_to_gemini():
                    try:
                        while True:
                            msg = await websocket.receive()
                            if "bytes" in msg and msg["bytes"]:
                                await live_session.send(input={"data": msg["bytes"], "mime_type": "audio/pcm"})
                            elif "text" in msg and msg["text"]:
                                data = json.loads(msg["text"])
                                mtype = data.get("type", "")

                                if mtype == "text_prompt":
                                    prompt_text = data.get("text", "")
                                    await live_session.send(input=prompt_text or ".", end_of_turn=True)
                                elif mtype == "end_of_turn":
                                    await live_session.send(input=".", end_of_turn=True)
                                elif mtype == "delegate_task":
                                    goal = data.get("goal", "")
                                    task_id = await orch.spawn_background_task(goal, is_voice_mode=True)
                                    await websocket.send_json({
                                        "type": "task_spawned",
                                        "task_id": task_id,
                                        "message": f"Delegated '{goal}' to background engine.",
                                    })
                    except WebSocketDisconnect:
                        logger.info("🎤 Voice Client WebSocket disconnected.")
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Error in client_to_gemini voice bridge: {e}")

                async def gemini_to_client():
                    try:
                        while True:
                            turn = live_session.receive()
                            async for response in turn:
                                # 1. Handle Native Tool Calls from Gemini Live
                                if getattr(response, 'tool_call', None) and response.tool_call.function_calls:
                                    function_responses = []
                                    for fc in response.tool_call.function_calls:
                                        fn_name = fc.name
                                        fn_args = dict(fc.args or {})
                                        logger.info(f'[GeminiLiveTool] Invoking {fn_name}({fn_args})')
                                        await websocket.send_json({
                                            'type': 'status',
                                            'text': (
                                                f'Gemini 3.8 Extended Thinking: {fn_args.get("problem", "")[:45]}...'
                                                if fn_name == 'deep_think_gemini_3_8'
                                                else f'Executing: {fn_args.get("goal", "")[:45]}...'
                                            ),
                                        })

                                        if fn_name == 'deep_think_gemini_3_8':
                                            res_dict = await orch.run_extended_thinking_query(
                                                problem=str(fn_args.get('problem', ''))
                                            )
                                            if res_dict.get('thoughts'):
                                                await websocket.send_json({
                                                    'type': 'thought',
                                                    'model': res_dict.get('model', 'gemini-3.8-flash'),
                                                    'text': res_dict['thoughts'],
                                                })
                                            tool_output = res_dict.get('answer', '')
                                        elif fn_name == 'execute_dione_action':
                                            tool_output = await orch.execute_action_for_live_voice(
                                                goal=str(fn_args.get('goal', ''))
                                            )
                                            await websocket.send_json({
                                                'type': 'transcript',
                                                'role': 'model',
                                                'text': tool_output,
                                            })
                                        else:
                                            tool_output = f'Unknown tool {fn_name}'

                                        function_responses.append(
                                            types.FunctionResponse(
                                                id=fc.id,
                                                name=fn_name,
                                                response={'result': str(tool_output)},
                                            )
                                        )

                                    if function_responses:
                                        await live_session.send_tool_response(function_responses=function_responses)

                                # 2. Direct PCM Audio Streaming from response.data
                                data = getattr(response, 'data', None)
                                if data:
                                    await websocket.send_bytes(data)

                                # 3. Fallback parts from server_content & Text Transcripts
                                sc = getattr(response, 'server_content', None)
                                if sc and sc.model_turn:
                                    for part in sc.model_turn.parts:
                                        if not data and part.inline_data and part.inline_data.data:
                                            await websocket.send_bytes(part.inline_data.data)
                                        if part.text:
                                            await websocket.send_json({
                                                'type': 'transcript',
                                                'role': 'model',
                                                'text': part.text,
                                            })
                                if getattr(response, 'text', None):
                                    await websocket.send_json({
                                        'type': 'transcript',
                                        'role': 'model',
                                        'text': response.text,
                                    })
                                if sc and sc.turn_complete:
                                    await websocket.send_json({'type': 'turn_complete'})
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f'Error in gemini_to_client audio stream: {e}')

                t1 = asyncio.create_task(client_to_gemini())
                t2 = asyncio.create_task(gemini_to_client())
                done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
                for p in pending:
                    p.cancel()
                break
        except Exception as live_err:
            last_err = live_err
            logger.warning(f"Gemini Live model {live_model} failed: {live_err}")
            continue

    if not connected_session and last_err:
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Gemini Live connection failed: {last_err}",
            })
        except Exception:
            pass