"""
Dione AI — Dual-Model Gemini Live Frontman + Gemini 3.8 Extended Thinking & Unified ReAct Core
==============================================================================================
Manages:
1. Gemini Live API as the low-latency Conversational Voice Frontman (24kHz out / 16kHz in).
2. Gemini 3.8 Flash (`gemini-3.8-flash`) with Extended Thinking (`ThinkingConfig`) for deep
   reasoning, architecture analysis, math, and multi-step planning during live voice or chat.
3. Direct synchronous & background tool delegation to `DioneEngine` (Computer-Use, Gmail,
   Calendar, Drive, Photos, WhatsApp, Telegram, Slack, Instagram, Web, Filesystem).
"""

from __future__ import annotations

import asyncio
import os
import uuid
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from server.config.settings import get_settings
from server.core.orchestrator import get_multi_agent_orchestrator


@dataclass
class LiveFlashConfig:
    live_frontman_model: str = "gemini-2.5-flash-native-audio-latest"
    reasoning_model: str = "gemini-3.8-flash"
    background_flash_model: str = "gemini-3.5-flash-lite"
    thinking_budget: int = 8192
    voice_name: str = "Aoede"


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
            env_key = os.getenv("DIONE_LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
            if env_key:
                self.keys.append(env_key.strip())
        if not self.keys:
            return None
        key = self.keys[self._index % len(self.keys)]
        self._index += 1
        return key


class LiveFlashOrchestrator:
    """
    Coordinates Gemini Live Frontman voice interactions with:
    - Gemini 3.8 Extended Thinking (`deep_think_gemini_3_8`)
    - Unified DioneEngine OS & Service Execution (`execute_dione_action`)
    """

    def __init__(self):
        self.config = LiveFlashConfig()
        self.key_pool = KeyPool()
        self.task_results: Dict[str, Dict[str, Any]] = {}
        self.orchestrator = get_multi_agent_orchestrator()
        logger.info(
            f"🎙️ LiveFlashOrchestrator initialized | Live: {self.config.live_frontman_model} | "
            f"Reasoning: {self.config.reasoning_model} (thinking={self.config.thinking_budget}) | Voice: {self.config.voice_name}"
        )

    def update_config(
        self,
        api_keys: Optional[List[str]] = None,
        live_model: Optional[str] = None,
        reasoning_model: Optional[str] = None,
        flash_model: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        voice_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if api_keys:
            self.key_pool.add_keys(api_keys)
        if live_model:
            self.config.live_frontman_model = live_model
        if reasoning_model:
            self.config.reasoning_model = reasoning_model
        if flash_model:
            self.config.background_flash_model = flash_model
        if thinking_budget is not None:
            self.config.thinking_budget = int(thinking_budget)
        if voice_name:
            self.config.voice_name = voice_name

        return {
            "live_frontman_model": self.config.live_frontman_model,
            "reasoning_model": self.config.reasoning_model,
            "background_flash_model": self.config.background_flash_model,
            "thinking_budget": self.config.thinking_budget,
            "voice_name": self.config.voice_name,
            "keys_count": len(self.key_pool.keys),
        }

    async def execute_action_for_live_voice(self, goal: str) -> str:
        """
        Executes a workstation or multi-service goal through DioneEngine and returns
        the concise spoken synthesis so the Live Voice session can report back immediately.
        """
        task_id = f"live_act_{uuid.uuid4().hex[:6]}"
        start_t = time.perf_counter()
        self.task_results[task_id] = {
            "task_id": task_id,
            "goal": goal,
            "status": "running",
            "delegated_to": self.config.background_flash_model,
            "started_at": datetime.now().isoformat(),
        }
        try:
            session = await self.orchestrator.execute_orchestrated_goal(goal, is_voice_mode=True)
            latency = round((time.perf_counter() - start_t) * 1000, 1)
            self.task_results[task_id].update({
                "status": "completed",
                "final_synthesis": session.final_synthesis,
                "latency_ms": latency,
            })
            return session.final_synthesis or "Action completed successfully."
        except Exception as e:
            logger.error(f"[LiveFlashOrchestrator] Action execution error: {e}")
            self.task_results[task_id].update({"status": "failed", "error": str(e)})
            return f"Encountered an issue executing that action: {e}"

    async def run_extended_thinking_query(self, problem: str, thinking_budget: Optional[int] = None) -> Dict[str, str]:
        """
        Invokes Gemini 3.8 Flash (with failover to Gemini 2.5 Pro / 2.5 Flash) using
        Extended Thinking (`ThinkingConfig`) plus Knowledge Graph and Memory context.
        """
        api_key = self.key_pool.get_active_key()
        if not api_key:
            return {"thoughts": "", "answer": "No Gemini API key configured."}

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        budget = thinking_budget or self.config.thinking_budget or 8192

        # Gather compact Knowledge Graph & Memory context if available
        context_snippets = []
        eng = self.orchestrator.engine
        if eng and eng._knowledge_graph:
            try:
                kg_ctx = await eng._knowledge_graph.query_relevant(problem, max_results=3)
                if kg_ctx:
                    context_snippets.append(f"Knowledge Graph: {kg_ctx}")
            except Exception:
                pass

        full_prompt = problem
        if context_snippets:
            full_prompt = "\\n".join(context_snippets) + f"\\n\\nUser Question / Problem:\\n{problem}"

        candidates = [
            self.config.reasoning_model,
            "gemini-3.8-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-3.5-flash-lite",
        ]
        candidates = list(dict.fromkeys([c for c in candidates if c]))

        for model_id in candidates:
            try:
                # Try with ThinkingConfig first for models that support extended thinking
                try:
                    cfg = types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=2048,
                        thinking_config=types.ThinkingConfig(
                            include_thoughts=True,
                            thinking_budget=min(max(1024, budget), 16384),
                        ),
                        system_instruction=(
                            "You are Dione's Gemini 3.8 Extended Thinking Reasoning Core. "
                            "Reason step-by-step through the problem, then provide a clear, accurate, "
                            "concise answer suitable for spoken and written delivery."
                        ),
                    )
                    resp = await client.aio.models.generate_content(
                        model=model_id,
                        contents=full_prompt,
                        config=cfg,
                    )
                except Exception:
                    # Fallback if specific model or SDK version rejects ThinkingConfig
                    cfg = types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=2048,
                        system_instruction=(
                            "You are Dione's Gemini 3.8 Extended Thinking Reasoning Core. "
                            "Think carefully and provide a precise, high-signal answer."
                        ),
                    )
                    resp = await client.aio.models.generate_content(
                        model=model_id,
                        contents=full_prompt,
                        config=cfg,
                    )

                thoughts_list = []
                answer_list = []
                if resp and resp.candidates:
                    for part in (resp.candidates[0].content.parts or []):
                        if getattr(part, "thought", False) and part.text:
                            thoughts_list.append(part.text)
                        elif part.text:
                            answer_list.append(part.text)

                final_ans = "\\n".join(answer_list).strip() or (resp.text or "").strip()
                return {
                    "model": model_id,
                    "thoughts": "\\n".join(thoughts_list).strip(),
                    "answer": final_ans,
                }
            except Exception as e:
                logger.warning(f"[ExtendedThinking] Candidate {model_id} failed: {e}")
                continue

        return {"model": "fallback", "thoughts": "", "answer": "Could not complete extended thinking request."}

    async def spawn_background_task(self, goal: str, is_voice_mode: bool = True) -> str:
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
        start_t = time.perf_counter()
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
        except Exception as e:
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

GeminiLiveOrchestrator = LiveFlashOrchestrator
