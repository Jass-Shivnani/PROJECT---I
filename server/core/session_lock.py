"""
Dione AI — Sessional Write Lock
===============================
Ported from OpenClaw's session-write-lock.ts:
Guarantees sequential, thread-safe message dispatching per session key.
Prevents concurrent prompt interleaving and state corruption.
"""

from __future__ import annotations

import asyncio
from typing import Dict
from loguru import logger


class SessionLockManager:
    """Provides per-session asynchronous locks."""

    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}

    def get_lock(self, session_key: str) -> asyncio.Lock:
        if session_key not in self._locks:
            self._locks[session_key] = asyncio.Lock()
        return self._locks[session_key]


_lock_manager: SessionLockManager | None = None


def get_session_lock_manager() -> SessionLockManager:
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = SessionLockManager()
    return _lock_manager
