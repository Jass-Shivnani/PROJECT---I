"""
Dione AI — Audio & Dual-Model Gemini Live + Background Flash Routes
====================================================================
WebSocket and REST endpoints for real-time voice conversations using
Gemini Live API as the low-latency Frontman and unified DioneEngine as
the background OS automation & heavy-lifting core.
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

router = APIRouter()


class AIStudioConfigPayload(BaseModel):
    api_keys: Optional[List[str]] = None
    live_frontman_model: Optional[str] = "gemini-2.5-flash-native-audio-latest"
    background_flash_model: Optional[str] = "gemini-3.5-flash-lite"
    voice_name: Optional[str] = "Aoede"


class BackgroundTaskPayload(BaseModel):
    goal: str


@router.post("/aistudio-config")
async def update_aistudio_config(payload: AIStudioConfigPayload):
    """
    Configure Google AI Studio API keys and select the Gemini Live Frontman model
    and Background Gemini Flash worker model.
    """
    orch = get_live_flash_orchestrator()
    updated = orch.update_config(
        api_keys=payload.api_keys,
        live_model=payload.live_frontman_model,
        flash_model=payload.background_flash_model,
        voice_name=payload.voice_name,
    )
    return {"success": True, "config": updated}


@router.get("/aistudio-config")
async def get_aistudio_config():
    """Return current Dual-Model Gemini Live + Background Flash configuration."""
    orch = get_live_flash_orchestrator()
    return {
        "live_frontman_model": orch.config.live_frontman_model,
        "background_flash_model": orch.config.background_flash_model,
        "voice_name": orch.config.voice_name,
        "configured_keys_count": len(orch.key_pool.keys),
        "active_tasks": list(orch.task_results.values()),
    }


@router.post("/spawn-flash-task")
async def spawn_background_flash_task(payload: BackgroundTaskPayload):
    """
    Non-blocking endpoint called by the Gemini Live Frontman (or UI)
    to spawn a background task executed through the unified DioneEngine.
    """
    orch = get_live_flash_orchestrator()
    task_id = await orch.spawn_background_task(payload.goal, is_voice_mode=True)
    return {
        "success": True,
        "task_id": task_id,
        "status": "running",
        "delegated_to": orch.config.background_flash_model,
    }


@router.post("/transcribe")
async def transcribe_audio(request: Request):
    """Transcribe uploaded audio to text."""
    body = await request.json()
    audio_b64 = body.get("audio_base64", "")
    mime_type = body.get("mime_type", "audio/wav")

    if not audio_b64:
        return {"error": "No audio data provided"}

    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception:
        return {"error": "Invalid base64 audio data"}

    if not hasattr(request.app.state, "audio") or not request.app.state.audio:
        return {"error": "Audio not configured. Set GEMINI_API_KEY in .env"}

    try:
        audio = request.app.state.audio
        ext = mime_type.split("/")[-1] if "/" in mime_type else "wav"
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            text = await audio.transcribe(temp_path)
            return {"text": text, "success": True}
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {"error": str(e), "success": False}


@router.post("/tts")
async def text_to_speech(request: Request):
    """Convert text to speech audio."""
    body = await request.json()
    text = body.get("text", "")

    if not text:
        return {"error": "No text provided"}

    if not hasattr(request.app.state, "audio") or not request.app.state.audio:
        return {"error": "Audio not configured"}

    try:
        audio_bytes = await request.app.state.audio.text_to_speech(text)
        if audio_bytes:
            return {
                "audio_base64": base64.b64encode(audio_bytes).decode(),
                "mime_type": "audio/wav",
                "success": True,
            }
        return {"error": "No audio generated", "success": False}
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return {"error": str(e), "success": False}


@router.websocket("/live")
async def audio_live_session(websocket: WebSocket):
    """
    Full-Duplex Bidirectional WebSocket endpoint for Gemini Live Frontman.
    Streams 16kHz PCM from browser mic -> Gemini Live API -> Streams 24kHz PCM back to browser speaker.
    """
    await websocket.accept()
    logger.info("🎤 Gemini Live Neural Voice WebSocket connected")
    orch = get_live_flash_orchestrator()

    api_key = (
        orch.key_pool.get_active_key()
        or os.getenv("DIONE_LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )
    if not api_key:
        await websocket.send_json({"type": "error", "message": "No Gemini API key available"})
        await websocket.close()
        return

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    live_model = orch.config.live_frontman_model or "gemini-2.5-flash-native-audio-latest"

    cfg = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=orch.config.voice_name or "Aoede"
                )
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(
                text="You are Dione, an executive, proactive, highly competent personal AI assistant (Jarvis persona). "
                     "Speak with poise, warmth, and precision. Deliver answers formatted for fluid conversational speech: "
                     "concise, refined, and completely free of markdown syntax or bullet asterisks."
            )]
        ),
    )

    try:
        async with client.aio.live.connect(model=live_model, config=cfg) as live_session:
            await websocket.send_json({
                "type": "session_ready",
                "model": live_model,
                "voice": orch.config.voice_name,
            })

            # Task 1: Receive from Client Browser -> Send to Gemini Live
            async def client_to_gemini():
                try:
                    while True:
                        msg = await websocket.receive()
                        if "bytes" in msg and msg["bytes"]:
                            # Raw PCM 16kHz audio chunk from user microphone (filtered by client VAD)
                            await live_session.send_realtime_input(
                                media={"data": msg["bytes"], "mime_type": "audio/pcm;rate=16000"}
                            )
                        elif "text" in msg and msg["text"]:
                            data = json.loads(msg["text"])
                            mtype = data.get("type", "")

                            if mtype == "text_prompt":
                                prompt_text = data.get("text", "")
                                await live_session.send_client_content(
                                    turns=[types.Content(parts=[types.Part.from_text(text=prompt_text)])],
                                    turn_complete=True,
                                )

                            elif mtype == "wake_word":
                                await live_session.send_client_content(
                                    turns=[types.Content(parts=[types.Part.from_text(text="Sir, I am listening and at your command.")])],
                                    turn_complete=True,
                                )

                            elif mtype == "end_of_turn":
                                await live_session.send_client_content(turn_complete=True)

                            elif mtype == "delegate_task":
                                goal = data.get("goal", "")
                                task_id = await orch.spawn_background_task(goal, is_voice_mode=True)
                                await websocket.send_json({
                                    "type": "task_spawned",
                                    "task_id": task_id,
                                    "message": f"Delegated '{goal}' to background execution core.",
                                })
                except WebSocketDisconnect:
                    logger.info("🎤 Voice Client WebSocket disconnected.")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error in client_to_gemini voice bridge: {e}")

            # Task 2: Receive from Gemini Live -> Stream to Client Browser
            async def gemini_to_client():
                try:
                    async for response in live_session.receive():
                        sc = response.server_content
                        if sc and sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    # Send raw 24kHz PCM audio frame to browser for low-latency playback
                                    await websocket.send_bytes(part.inline_data.data)
                                if part.text:
                                    await websocket.send_json({
                                        "type": "transcript",
                                        "role": "model",
                                        "text": part.text,
                                    })
                        if sc and sc.turn_complete:
                            await websocket.send_json({"type": "turn_complete"})
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error in gemini_to_client audio stream: {e}")

            t1 = asyncio.create_task(client_to_gemini())
            t2 = asyncio.create_task(gemini_to_client())

            done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()

    except Exception as live_err:
        logger.error(f"Gemini Live session error: {live_err}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Gemini Live session error: {live_err}",
            })
        except Exception:
            pass
