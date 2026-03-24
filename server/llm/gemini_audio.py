"""
Dione AI — Gemini Audio / Live API Adapter

Adds voice/audio capabilities to Dione using Google's Gemini Live API.
This lets the user have spoken conversations with Dione.

The Live API uses WebSocket connections for real-time, multi-turn
voice conversations with low latency.

Usage:
    audio = GeminiAudioAdapter(api_key="...", model="gemini-2.0-flash-live-001")
    session = await audio.create_session()
    await session.send_audio(audio_bytes)
    response = await session.receive()
"""

import asyncio
import base64
import json
import time
from typing import AsyncGenerator, Optional
from pathlib import Path
from loguru import logger


class AudioSession:
    """
    A live audio session with Gemini.
    
    Wraps the Gemini Live API's WebSocket-based session
    for real-time audio input/output.
    """
    
    def __init__(self, client, model: str, system_instruction: str = ""):
        self._client = client
        self._model = model
        self._system_instruction = system_instruction
        self._session = None
        self._active = False
    
    async def connect(self) -> bool:
        """Start a live session."""
        try:
            from google.genai import types
            
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO", "TEXT"],
            )
            if self._system_instruction:
                config.system_instruction = types.Content(
                    parts=[types.Part(text=self._system_instruction)]
                )
            
            self._session = await self._client.aio.live.connect(
                model=self._model,
                config=config,
            )
            self._active = True
            logger.info(f"Audio session connected: {self._model}")
            return True
        except Exception as e:
            logger.error(f"Audio session connect failed: {e}")
            return False
    
    async def send_text(self, text: str) -> None:
        """Send text input to the live session."""
        if not self._session or not self._active:
            raise RuntimeError("No active audio session")
        await self._session.send(input=text, end_of_turn=True)
    
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> None:
        """
        Send raw audio data to the live session.
        
        Args:
            audio_data: Raw audio bytes (PCM 16-bit, 16kHz mono recommended)
            mime_type: Audio format, default is raw PCM
        """
        if not self._session or not self._active:
            raise RuntimeError("No active audio session")
        
        from google.genai import types
        
        await self._session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(data=audio_data, mime_type=mime_type)
                ]
            )
        )
    
    async def receive_text(self) -> str:
        """Receive text response from the session."""
        if not self._session or not self._active:
            return ""
        
        full_text = ""
        try:
            async for response in self._session.receive():
                if hasattr(response, 'text') and response.text:
                    full_text += response.text
                if hasattr(response, 'server_content'):
                    sc = response.server_content
                    if hasattr(sc, 'turn_complete') and sc.turn_complete:
                        break
        except Exception as e:
            logger.error(f"Audio receive error: {e}")
        
        return full_text
    
    async def receive_audio(self) -> AsyncGenerator[bytes, None]:
        """
        Receive audio response chunks from the session.
        
        Yields raw audio bytes that can be played back.
        """
        if not self._session or not self._active:
            return
        
        try:
            async for response in self._session.receive():
                if hasattr(response, 'server_content'):
                    sc = response.server_content
                    if hasattr(sc, 'model_turn') and sc.model_turn:
                        for part in sc.model_turn.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                yield part.inline_data.data
                    if hasattr(sc, 'turn_complete') and sc.turn_complete:
                        break
        except Exception as e:
            logger.error(f"Audio stream error: {e}")
    
    async def close(self) -> None:
        """Close the audio session."""
        self._active = False
        if self._session:
            try:
                await self._session.close()
            except Exception:
                pass
            self._session = None
        logger.info("Audio session closed")
    
    @property
    def is_active(self) -> bool:
        return self._active


class GeminiAudioAdapter:
    """
    High-level audio adapter for Dione.
    
    Manages audio sessions and provides methods for:
    - Text-to-speech (TTS) via Gemini
    - Speech-to-text (STT) via Gemini  
    - Real-time voice conversations
    - Audio file transcription
    """
    
    LIVE_MODEL = "gemini-2.0-flash-live-001"
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._initialized = False
        self._active_session: Optional[AudioSession] = None
    
    def _ensure_client(self):
        """Lazy-initialize the Gemini client."""
        if self._initialized:
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            self._initialized = True
            logger.info("Gemini Audio adapter initialized")
        except ImportError:
            raise RuntimeError(
                "google-genai is not installed. "
                "Install with: pip install google-genai"
            )
    
    async def create_session(self, system_instruction: str = "") -> AudioSession:
        """
        Create a new real-time audio conversation session.
        
        Args:
            system_instruction: Optional system prompt for the session
            
        Returns:
            An AudioSession for real-time conversation
        """
        self._ensure_client()
        session = AudioSession(
            client=self._client,
            model=self.LIVE_MODEL,
            system_instruction=system_instruction,
        )
        await session.connect()
        self._active_session = session
        return session
    
    async def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file to text using Gemini.
        
        Args:
            audio_path: Path to the audio file (wav, mp3, etc.)
            
        Returns:
            Transcribed text
        """
        self._ensure_client()
        
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Determine MIME type
        ext = path.suffix.lower()
        mime_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mp3",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".m4a": "audio/mp4",
            ".webm": "audio/webm",
        }
        mime_type = mime_types.get(ext, "audio/wav")
        
        audio_data = path.read_bytes()
        
        from google.genai import types
        
        response = self._client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(parts=[
                    types.Part(text="Transcribe this audio accurately. Return only the transcription."),
                    types.Part(inline_data=types.Blob(
                        data=audio_data,
                        mime_type=mime_type,
                    )),
                ])
            ],
        )
        
        return response.text or ""
    
    async def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech audio using Gemini.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio bytes (WAV format)
        """
        self._ensure_client()
        
        from google.genai import types
        
        response = self._client.models.generate_content(
            model=self.model,
            contents=f"Read the following text aloud naturally: {text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
            ),
        )
        
        # Extract audio data from response
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    return part.inline_data.data
        
        return b""
    
    async def voice_chat(self, audio_bytes: bytes, 
                         system_instruction: str = "") -> tuple[str, bytes]:
        """
        Single-turn voice chat: send audio, get text + audio back.
        
        Args:
            audio_bytes: Input audio (PCM 16-bit, 16kHz)
            system_instruction: Optional instruction
            
        Returns:
            Tuple of (text_response, audio_response_bytes)
        """
        session = await self.create_session(system_instruction)
        try:
            await session.send_audio(audio_bytes)
            
            text = ""
            audio = b""
            
            async for response in session._session.receive():
                if hasattr(response, 'text') and response.text:
                    text += response.text
                if hasattr(response, 'server_content'):
                    sc = response.server_content
                    if hasattr(sc, 'model_turn') and sc.model_turn:
                        for part in sc.model_turn.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                audio += part.inline_data.data
                    if hasattr(sc, 'turn_complete') and sc.turn_complete:
                        break
            
            return text, audio
        finally:
            await session.close()
    
    @property
    def has_active_session(self) -> bool:
        return self._active_session is not None and self._active_session.is_active
    
    async def close(self):
        """Close any active session."""
        if self._active_session:
            await self._active_session.close()
            self._active_session = None
