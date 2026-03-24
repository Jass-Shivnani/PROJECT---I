"""
Dione AI — Audio Routes

WebSocket and REST endpoints for voice conversations using
Gemini Audio (Live API).
"""

import base64
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from loguru import logger


router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio(request: Request):
    """
    Transcribe uploaded audio to text.
    
    Expects JSON: {"audio_base64": "...", "mime_type": "audio/wav"}
    """
    body = await request.json()
    audio_b64 = body.get("audio_base64", "")
    mime_type = body.get("mime_type", "audio/wav")
    
    if not audio_b64:
        return {"error": "No audio data provided"}
    
    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception:
        return {"error": "Invalid base64 audio data"}
    
    # Check if audio adapter is available
    if not hasattr(request.app.state, "audio") or not request.app.state.audio:
        return {"error": "Audio not configured. Set GEMINI_API_KEY in .env"}
    
    try:
        audio = request.app.state.audio
        # Write to temp file for transcription
        import tempfile
        import os
        
        ext = mime_type.split("/")[-1] if "/" in mime_type else "wav"
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            text = await audio.transcribe(temp_path)
            return {"text": text, "success": True}
        finally:
            os.unlink(temp_path)
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {"error": str(e), "success": False}


@router.post("/tts")
async def text_to_speech(request: Request):
    """
    Convert text to speech audio.
    
    Expects JSON: {"text": "Hello world"}
    Returns: {"audio_base64": "...", "mime_type": "audio/wav"}
    """
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
    WebSocket endpoint for real-time voice conversation.
    
    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 audio>"}
    - Client sends: {"type": "text", "data": "hello"}  
    - Server sends: {"type": "text", "data": "response text"}
    - Server sends: {"type": "audio", "data": "<base64 audio>"}
    - Server sends: {"type": "turn_complete"}
    """
    await websocket.accept()
    logger.info("Audio WebSocket connected")
    
    audio_adapter = getattr(websocket.app.state, "audio", None)
    if not audio_adapter:
        await websocket.send_json({"type": "error", "data": "Audio not configured"})
        await websocket.close()
        return
    
    session = None
    try:
        # Get system instruction from engine
        engine = getattr(websocket.app.state, "engine", None)
        system_instruction = ""
        if engine and hasattr(engine, "_build_system_prompt"):
            system_instruction = engine._build_system_prompt()
        
        session = await audio_adapter.create_session(system_instruction)
        
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            
            if msg_type == "audio":
                audio_bytes = base64.b64decode(data.get("data", ""))
                await session.send_audio(audio_bytes)
                
                # Receive response
                text_response = await session.receive_text()
                if text_response:
                    await websocket.send_json({
                        "type": "text",
                        "data": text_response,
                    })
                await websocket.send_json({"type": "turn_complete"})
            
            elif msg_type == "text":
                await session.send_text(data.get("data", ""))
                text_response = await session.receive_text()
                if text_response:
                    await websocket.send_json({
                        "type": "text",
                        "data": text_response,
                    })
                await websocket.send_json({"type": "turn_complete"})
            
            elif msg_type == "close":
                break
    
    except WebSocketDisconnect:
        logger.info("Audio WebSocket disconnected")
    except Exception as e:
        logger.error(f"Audio WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
    finally:
        if session:
            await session.close()
