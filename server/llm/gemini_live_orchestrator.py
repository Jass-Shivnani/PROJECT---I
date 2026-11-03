"""
Dione AI — Dual-Model Gemini Live Frontman + Unified ReAct Core
===============================================================
Manages:
1. Gemini Live API as the low-latency Conversational Frontman (gemini-2.5-flash-native-audio-latest, Aoede/Puck voice)
2. Real-time bi-directional full-duplex PCM audio streaming (24kHz / 16kHz)
3. Background delegation to DioneEngine with is_voice_mode=True for heavy lifting & OS automation
4. Google AI Studio API key pool management
"""

from __future__ import annotations

import asyncio
import os
import uuid
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from datetime import datetime
from loguru import logger

from server.config.settings import get_settings
from server.core.orchestrator import get_multi_agent_orchestrator


@dataclass
class LiveFlashConfig:
    live_frontman_model: str = "gemini-2.5-flash-native-audio-latest"
    background_flash_model: str = "gemini-3.5-flash-lite"
    voice_name: str = "Aoede"  # Aoede (elegant assistant) or Puck (crisp executive)


class KeyPool:
    """Manages pool of Google AI Studio API keys for parallel execution."""

    def __init__(self, initial_keys: Optional[List[str]] = None):
        self.keys: List[str] = []
        if initial_keys:
            self.keys.extend([k.strip() for k in initial_keys if k and k.strip()])

        if not self.keys:
            settings = get_settings()
            env_key = (
                getattr(settings.llm, "api_key", None)
                or os.getenv("DIONE_LLM_API_KEY")
                or os.getenv("GEMINI_API_KEY")
            )
            if env_key:
                self.keys.append(env_key.strip())

        self._index = 0

    def add_keys(self, new_keys: List[str]):
        for k in new_keys:
            cleaned = k.strip()
            if cleaned and cleaned not in self.keys:
                self.keys.append(cleaned)

    def get_active_key(self) -> Optional[str]:
        if not self.keys:
            return None
        key = self.keys[self._index % len(self.keys)]
        self._index += 1
        return key


class LiveFlashOrchestrator:
    """
    Coordinates Gemini Live Frontman voice interactions with background
    task execution via the unified DioneEngine.
    """

    def __init__(self):
        self.config = LiveFlashConfig()
        self.key_pool = KeyPool()
        self.task_results: Dict[str, Dict[str, Any]] = {}
        self.orchestrator = get_multi_agent_orchestrator()
        logger.info(f"🎙️ LiveFlashOrchestrator initialized. Frontman: {self.config.live_frontman_model}, Voice: {self.config.voice_name}")

    def update_config(
        self,
        api_keys: Optional[List[str]] = None,
        live_model: Optional[str] = None,
        flash_model: Optional[str] = None,
        voice_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update active model parameters and API key pool."""
        if api_keys:
            self.key_pool.add_keys(api_keys)
        if live_model:
            self.config.live_frontman_model = live_model
        if flash_model:
            self.config.background_flash_model = flash_model
        if voice_name:
            self.config.voice_name = voice_name

        logger.info(
            f"[LiveFlashOrchestrator] Updated: live={self.config.live_frontman_model}, "
            f"bg_flash={self.config.background_flash_model}, voice={self.config.voice_name}, keys={len(self.key_pool.keys)}"
        )
        return {
            "live_frontman_model": self.config.live_frontman_model,
            "background_flash_model": self.config.background_flash_model,
            "voice_name": self.config.voice_name,
            "keys_count": len(self.key_pool.keys),
        }

    async def spawn_background_task(self, goal: str, is_voice_mode: bool = True) -> str:
        """
        Non-blocking invocation called by Frontman to dispatch goals
        to DioneEngine in the background while voice dialogue continues.
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.task_results[task_id] = {
            "task_id": task_id,
            "goal": goal,
            "status": "running",
            "delegated_to": self.config.background_flash_model,
            "started_at": datetime.now().isoformat(),
            "nodes": [],
            "final_synthesis": "",
        }

        asyncio.create_task(self._run_task_worker(task_id, goal, is_voice_mode))
        return task_id

    async def _run_task_worker(self, task_id: str, goal: str, is_voice_mode: bool = True):
        """Worker task executing tools through DioneEngine."""
        start_t = time.perf_counter()
        logger.info(f"[LiveFlashWorker] 🚀 Background task {task_id} started for: '{goal}'")
        try:
            session = await self.orchestrator.execute_orchestrated_goal(goal, is_voice_mode=is_voice_mode)
            latency = (time.perf_counter() - start_t) * 1000

            self.task_results[task_id].update({
                "status": "completed",
                "nodes": [n.to_dict() for n in session.nodes],
                "final_synthesis": session.final_synthesis,
                "latency_ms": round(latency, 1),
                "completed_at": datetime.now().isoformat(),
            })
            logger.info(f"[LiveFlashWorker] ✅ Background task {task_id} finished in {round(latency, 1)}ms: {session.final_synthesis[:60]}...")
        except Exception as e:
            logger.error(f"[LiveFlashWorker] ❌ Background task {task_id} failed: {e}")
            self.task_results[task_id].update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat(),
            })


_live_flash_orchestrator: Optional[LiveFlashOrchestrator] = None


def get_live_flash_orchestrator() -> LiveFlashOrchestrator:
    global _live_flash_orchestrator
    if _live_flash_orchestrator is None:
        _live_flash_orchestrator = LiveFlashOrchestrator()
    return _live_flash_orchestrator

# Backward-compatible alias
GeminiLiveOrchestrator = LiveFlashOrchestrator
