"""
Dione Next-Gen — Tri-Actor Asynchronous Event Bus

Central non-blocking event-driven messaging backbone connecting:
1. Voice Frontman (VAD, STT, Spoken Bridges, TTS)
2. Cognitive Planner (GraphRAG, Multi-Step Planner, Reflection)
3. Computer-Use Operator (Windows UIA, Mouse, Keyboard, Filesystem, Apps)
4. Desktop Dynamic Island Overlay (WebView2, Telemetry, Approvals)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from loguru import logger


class EventType(str, Enum):
    # State & Lifecycle
    STATE_CHANGED = "state_changed"
    ERROR_OCCURRED = "error_occurred"
    EMERGENCY_STOP = "emergency_stop"
    RESUME_REQUESTED = "resume_requested"

    # Audio & Voice Pipeline
    VOICE_VAD_START = "voice_vad_start"
    VOICE_VAD_STOP = "voice_vad_stop"
    TRANSCRIPTION_INTERIM = "transcription_interim"
    TRANSCRIPTION_FINAL = "transcription_final"
    FILLER_GENERATED = "filler_generated"
    SPEECH_CHUNK = "speech_chunk"
    SPEECH_FINISHED = "speech_finished"
    VOICE_BARGE_IN = "voice_barge_in"

    # Cognitive Planning & GraphRAG
    GOAL_RECEIVED = "goal_received"
    PLAN_FORMULATED = "plan_formulated"
    THOUGHT_STREAM = "thought_stream"
    MEMORY_RETRIEVED = "memory_retrieved"

    # Tool & Computer-Use Execution
    TOOL_DISPATCHED = "tool_dispatched"
    TOOL_PROGRESS = "tool_progress"
    TOOL_COMPLETED = "tool_completed"
    COMPUTER_USE_ACTION = "computer_use_action"
    SCREENSHOT_CAPTURED = "screenshot_captured"

    # Safety Kernel Lattice
    SAFETY_APPROVAL_REQUEST = "safety_approval_request"
    SAFETY_APPROVAL_RESOLVED = "safety_approval_resolved"


class AgentState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ACTING = "acting"
    SPEAKING = "speaking"
    AWAITING_APPROVAL = "awaiting_approval"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class RuntimeEvent:
    """An immutable event packet dispatched across the runtime."""
    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    sender: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    event_id: str = field(default_factory=lambda: hex(id(object()))[2:])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.event_id,
            "type": self.event_type.value,
            "sender": self.sender,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


EventHandler = Callable[[RuntimeEvent], Coroutine[Any, Any, None]]


class AsyncEventBus:
    """
    High-throughput non-blocking asynchronous event bus.
    Enables low-latency actor coordination without lock contention.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._global_subscribers: List[EventHandler] = []
        self._state: AgentState = AgentState.IDLE
        self._event_history: List[RuntimeEvent] = []
        self._max_history = 100
        self._lock = asyncio.Lock()
        self._emergency_stopped = False

    @property
    def current_state(self) -> AgentState:
        return self._state

    @property
    def is_emergency_stopped(self) -> bool:
        return self._emergency_stopped

    def set_state(self, new_state: AgentState, reason: str = ""):
        old_state = self._state
        if old_state != new_state:
            self._state = new_state
            logger.debug(f"[EventBus] State: {old_state.value} -> {new_state.value} ({reason})")
            asyncio.create_task(
                self.publish(
                    RuntimeEvent(
                        event_type=EventType.STATE_CHANGED,
                        payload={"from": old_state.value, "to": new_state.value, "reason": reason},
                        sender="event_bus",
                    )
                )
            )

    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe an async handler to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler):
        """Subscribe to every event passing through the bus."""
        self._global_subscribers.append(handler)

    async def publish(self, event: RuntimeEvent):
        """Publish an event to all interested handlers concurrently."""
        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

        # Handle emergency stop state
        if event.event_type == EventType.EMERGENCY_STOP:
            self._emergency_stopped = True
            self.set_state(AgentState.PAUSED, reason=event.payload.get("reason", "Emergency stop"))
        elif event.event_type == EventType.RESUME_REQUESTED:
            self._emergency_stopped = False
            self.set_state(AgentState.IDLE, reason="Resumed")

        handlers = list(self._subscribers.get(event.event_type, [])) + list(self._global_subscribers)
        if not handlers:
            return

        # Fire and gather handlers
        tasks = [asyncio.create_task(self._safe_invoke(handler, event)) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_invoke(self, handler: EventHandler, event: RuntimeEvent):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"[EventBus] Handler {getattr(handler, '__name__', str(handler))} failed on {event.event_type}: {e}")

    def trigger_emergency_stop(self, reason: str = "User fail-safe triggered"):
        """Synchronously dispatch emergency stop."""
        logger.warning(f"[EventBus] 🚨 EMERGENCY STOP: {reason}")
        asyncio.create_task(
            self.publish(
                RuntimeEvent(
                    event_type=EventType.EMERGENCY_STOP,
                    payload={"reason": reason},
                    sender="fail_safe",
                )
            )
        )


# Global singleton instance
_global_bus: Optional[AsyncEventBus] = None


def get_event_bus() -> AsyncEventBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = AsyncEventBus()
    return _global_bus
