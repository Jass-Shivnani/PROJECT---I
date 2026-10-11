"""
Test Suite for Dione Next-Gen Tri-Actor Runtime Core
Verifies:
1. EventBus dispatch and emergency stop
2. FillerEngine domain routing and thinking phrase generation
3. ComputerUseOperator perception and safe operations
4. CognitivePlanner goal decomposition and routing
"""

import asyncio
import io
import sys
from pathlib import Path

# Fix Windows console UTF-8
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.core.runtime.event_bus import (
    AgentState,
    AsyncEventBus,
    EventType,
    RuntimeEvent,
)
from server.core.runtime.filler_engine import SpokenFillerEngine
from server.core.runtime.computer_use import ComputerUseOperator
from server.core.runtime.cognitive_planner import CognitivePlanner


async def test_event_bus():
    bus = AsyncEventBus()
    received_events = []

    async def sample_handler(event: RuntimeEvent):
        received_events.append(event)

    bus.subscribe(EventType.GOAL_RECEIVED, sample_handler)

    test_event = RuntimeEvent(
        event_type=EventType.GOAL_RECEIVED,
        payload={"goal": "Test goal"},
        sender="test_suite",
    )
    await bus.publish(test_event)

    assert len(received_events) == 1
    assert received_events[0].payload["goal"] == "Test goal"
    assert bus.current_state == AgentState.IDLE

    # Test emergency stop
    bus.trigger_emergency_stop("Test emergency stop")
    await asyncio.sleep(0.05)
    assert bus.is_emergency_stopped is True
    assert bus.current_state == AgentState.PAUSED
    print("✓ EventBus tests passed.")


def test_filler_engine():
    engine = SpokenFillerEngine()

    # Test domain detection
    assert engine.detect_domain("Can you check my WhatsApp messages from Alice?") == "whatsapp"
    assert engine.detect_domain("Open Spotify and play lofi beats") == "spotify_media"
    assert engine.detect_domain("Find the capstone PDF in my files") == "file"
    assert engine.detect_domain("What commitments did I make to Prof. Geocey?") == "knowledge_graph"

    # Test bridges
    opening = engine.get_opening_bridge("Open Spotify")
    assert isinstance(opening, str) and len(opening) > 5
    assert "Spotify" in opening or "music" in opening or "tuning" in opening

    res = engine.get_resolution_bridge()
    assert isinstance(res, str) and len(res) > 3
    print("✓ FillerEngine tests passed.")


async def test_computer_use_safe_ops():
    bus = AsyncEventBus()
    operator = ComputerUseOperator(event_bus=bus)

    # Test listing windows (safe read-only)
    windows = await operator.list_open_windows()
    assert isinstance(windows, list)

    # Test volume adjustment
    vol_res = await operator.adjust_volume("mute")
    assert "mute" in vol_res.lower() or "fail-safe" in vol_res.lower()
    print("✓ ComputerUse safe operations passed.")


async def test_cognitive_planner():
    bus = AsyncEventBus()
    operator = ComputerUseOperator(event_bus=bus)
    planner = CognitivePlanner(event_bus=bus, computer_use=operator)

    # Test planning a diagnostic goal
    res = await planner.execute_goal("How much RAM and CPU is currently free?")
    assert "RAM" in res or "CPU" in res

    # Test knowledge/social intelligence query
    res2 = await planner.execute_goal("What promises did I make to Prof. Geocey?")
    assert "Geocey" in res2
    print("✓ CognitivePlanner tests passed.")


async def main():
    print("========================================")
    print("🚀 RUNNING DIONE NEXT-GEN RUNTIME TESTS")
    print("========================================")
    await test_event_bus()
    test_filler_engine()
    await test_computer_use_safe_ops()
    await test_cognitive_planner()
    print("========================================")
    print("🎉 ALL NEXT-GEN RUNTIME TESTS PASSED!")
    print("========================================")


if __name__ == "__main__":
    asyncio.run(main())
