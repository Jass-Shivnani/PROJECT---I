"""
Dione Next-Gen — Voice Frontman Actor

High-performance conversational speech actor responsible for:
1. Real-time microphone capture & Voice Activity Detection (VAD)
2. Ultra-fast neural Text-to-Speech (Edge-TTS / Local synthesis)
3. Context-aware spoken bridge delivery ("Hmm, let me thinkkk...")
4. Instant barge-in / speech interruption handling
"""

import asyncio
import io
import os
import tempfile
from pathlib import Path
from typing import Optional
from loguru import logger

from server.core.runtime.event_bus import (
    AgentState,
    AsyncEventBus,
    EventType,
    RuntimeEvent,
    get_event_bus,
)
from server.core.runtime.filler_engine import SpokenFillerEngine, get_filler_engine


class VoiceFrontman:
    """
    Conversational Voice Frontman.
    Ensures zero dead-air latency by speaking conversational bridges
    while the cognitive planner and computer-use subagents run in parallel.
    """

    DEFAULT_VOICE = "en-US-ChristopherNeural"  # Expressive, warm neural voice

    def __init__(
        self,
        event_bus: Optional[AsyncEventBus] = None,
        filler_engine: Optional[SpokenFillerEngine] = None,
        voice_name: str = DEFAULT_VOICE,
    ):
        self.bus = event_bus or get_event_bus()
        self.fillers = filler_engine or get_filler_engine()
        self.voice_name = voice_name
        self._is_speaking = False
        self._current_playback_process = None
        self._playback_lock = asyncio.Lock()
        self._stop_requested = False

        # Register event handlers
        self.bus.subscribe(EventType.VOICE_BARGE_IN, self._handle_barge_in)
        self.bus.subscribe(EventType.EMERGENCY_STOP, self._handle_emergency_stop)

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    async def speak(self, text: str, is_filler: bool = False) -> bool:
        """
        Synthesize text using Edge-TTS and play it through default system audio.
        Non-blocking, interruptible.
        """
        if not text or not text.strip():
            return False

        if self.bus.is_emergency_stopped:
            logger.warning("[VoiceFrontman] Cannot speak: Emergency stop is active.")
            return False

        self._stop_requested = False
        self._is_speaking = True
        self.bus.set_state(AgentState.SPEAKING, reason=f"Speaking: {text[:40]}...")

        clean_text = text.strip()
        logger.info(f"[VoiceFrontman] 🗣️ Speaking ({'filler' if is_filler else 'response'}): {clean_text}")

        # Publish speech event to UI
        await self.bus.publish(
            RuntimeEvent(
                event_type=EventType.SPEECH_CHUNK,
                payload={"text": clean_text, "is_filler": is_filler},
                sender="voice_frontman",
            )
        )

        temp_audio_file = None
        try:
            import edge_tts

            # Generate speech file
            communicate = edge_tts.Communicate(clean_text, self.voice_name, rate="+5%", pitch="+0Hz")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_audio_file = f.name

            await communicate.save(temp_audio_file)

            if self._stop_requested:
                return False

            # Play audio file via native Windows media player or PowerShell sound player
            await self._play_audio_file(temp_audio_file)

            return True

        except Exception as e:
            logger.error(f"[VoiceFrontman] TTS playback failed: {e}")
            return False

        finally:
            self._is_speaking = False
            if temp_audio_file and os.path.exists(temp_audio_file):
                try:
                    os.unlink(temp_audio_file)
                except Exception:
                    pass

            await self.bus.publish(
                RuntimeEvent(
                    event_type=EventType.SPEECH_FINISHED,
                    payload={"text": clean_text},
                    sender="voice_frontman",
                )
            )

    async def _play_audio_file(self, audio_path: str):
        """Play an MP3 audio file asynchronously in Python without blocking."""
        import pygame
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                logger.error(f"[VoiceFrontman] pygame mixer init error: {e}")
                return

        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                if self._stop_requested:
                    pygame.mixer.music.stop()
                    break
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"[VoiceFrontman] Audio playback error: {e}")

    def stop_speech(self):
        """Immediately abort speech playback."""
        logger.info("[VoiceFrontman] 🛑 Aborting speech playback")
        self._stop_requested = True
        self._is_speaking = False
        try:
            import pygame
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except Exception:
            pass

    async def _handle_barge_in(self, event: RuntimeEvent):
        """Handle user interrupting the agent."""
        logger.info("[VoiceFrontman] User barge-in detected. Halting speech.")
        self.stop_speech()

    async def _handle_emergency_stop(self, event: RuntimeEvent):
        """Handle system-wide emergency stop."""
        self.stop_speech()

    async def bridge_and_execute(self, user_goal: str, executor_coro) -> str:
        """
        Orchestration pipeline:
        1. Emits instantaneous spoken filler ("Hmm, let me look into Alice's messages... hold on...")
        2. Concurrently executes the cognitive subagent or OS tool
        3. Emits victory bridge ("Aha, got it!")
        4. Speaks the final answer
        """
        # Step 1: Immediate contextual spoken filler
        opening_filler = self.fillers.get_opening_bridge(user_goal)
        filler_task = asyncio.create_task(self.speak(opening_filler, is_filler=True))

        # Step 2: Background execution concurrently with filler
        executor_task = asyncio.create_task(executor_coro)

        # Let filler finish or let executor finish
        await asyncio.gather(filler_task, return_exceptions=True)

        # Wait for cognitive subagent to finish
        self.bus.set_state(AgentState.THINKING, reason="Waiting for cognitive subagent")
        result = await executor_task

        # Step 3: Resolution interjection
        resolution = self.fillers.get_resolution_bridge()
        final_speech = f"{resolution} {result}"

        # Step 4: Spoken answer
        await self.speak(final_speech, is_filler=False)
        self.bus.set_state(AgentState.IDLE, reason="Turn completed")

        return result


# Global singleton
_voice_frontman: Optional[VoiceFrontman] = None


def get_voice_frontman() -> VoiceFrontman:
    global _voice_frontman
    if _voice_frontman is None:
        _voice_frontman = VoiceFrontman()
    return _voice_frontman
