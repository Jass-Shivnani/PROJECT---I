"""
Dione AI — Multi-Model Failover & Resiliency Chain (Google AI Studio Free Tier + AI Pro Trial)
==============================================================================================
Manages model fallback chains when encountering 429 Rate Limits (RPM/TPM/RPD),
503 Server Overload, or temporary quota exhaustion across Google AI Studio models.

Priority order for AI Studio Free Tier & AI Pro Trial:
1. gemini-3.5-flash-lite  (Highest Free Tier quota: 15 RPM / 500 RPD, ultra-low latency)
2. gemini-3.1-flash-lite  (Secondary high-quota Flash-Lite: 15 RPM / 500 RPD)
3. gemini-2.5-flash-lite  (Battle-tested high-throughput Flash-Lite: 10M batch tokens)
4. gemini-3.8-flash       (Latest flagship Flash reasoning model)
5. gemini-2.5-flash       (Balanced multimodal reasoning model)
6. gemini-2.5-pro         (Deep reasoning & complex coding in AI Pro trial)
7. gemini-flash-lite-latest (Evergreen alias)
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional
from loguru import logger

DEFAULT_GEMINI_CANDIDATES: List[str] = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
    "gemini-flash-lite-latest",
]


class ModelFailoverManager:
    """Manages model candidate priority and rate-limit cooldowns."""

    def __init__(self, candidates: Optional[List[str]] = None, cooldown_seconds: float = 60.0):
        self.candidates = list(candidates or DEFAULT_GEMINI_CANDIDATES)
        self.cooldown_seconds = cooldown_seconds
        self._cooldowns: Dict[str, float] = {}

    def get_available_candidates(self, preferred_model: Optional[str] = None) -> List[str]:
        """Returns preferred model (if healthy) followed by non-cooldown candidates, then expired cooldowns."""
        now = time.time()
        ordered_pool: List[str] = []
        if preferred_model and preferred_model.strip():
            ordered_pool.append(preferred_model.strip())
        for m in self.candidates:
            if m not in ordered_pool:
                ordered_pool.append(m)

        available = []
        in_cooldown = []

        for m in ordered_pool:
            cd_until = self._cooldowns.get(m, 0.0)
            if cd_until <= now:
                available.append(m)
            else:
                in_cooldown.append(m)

        return available if available else in_cooldown

    def mark_failure(self, model: str, reason: str = ""):
        """Puts a model in temporary cooldown (longer for daily quota exhaustion)."""
        now = time.time()
        r_low = str(reason).lower()
        cd = self.cooldown_seconds * 5 if ("perday" in r_low or "rpd" in r_low or "daily" in r_low) else self.cooldown_seconds
        self._cooldowns[model] = now + cd
        logger.warning(
            f"[Failover] Model {model} marked in cooldown for {cd:.0f}s. Reason: {str(reason)[:140]}"
        )

    def mark_success(self, model: str):
        """Clears any cooldown on successful execution."""
        if model in self._cooldowns:
            del self._cooldowns[model]
