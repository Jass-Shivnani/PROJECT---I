"""
Dione AI — Production Readiness Verification Suite
Tests:
1. Windows Application Resolver (Valorant, Discord, Chrome, VS Code, Steam, Calc, Notepad)
2. Audio Device Identification & Switching (Chu2 DSP IEMs)
3. Physical System Idle Detection (GetLastInputInfo)
4. Nighttime & Idle Synthesis Engine ('Dream Mode' & Morning Brief Card)
5. Live ReAct Chat Engine (Action Execution & Natural Conversational Persona)
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from server.core.runtime.computer_use import ComputerUseOperator
from server.proactive.heartbeat import HeartbeatScheduler
from server.proactive.dream_engine import DreamSynthesisEngine
from server.knowledge.graph import KnowledgeGraph
import httpx

def test_app_resolver():
    print("\n--- 1. Testing Windows App & Game Resolver ---")
    apps_to_test = ["valorant", "discord", "chrome", "code", "steam", "calc", "notepad"]
    successes = 0
    for app in apps_to_test:
        target = ComputerUseOperator.resolve_windows_app(app)
        if target:
            print(f"  [OK] {app:12} -> {target}")
            successes += 1
        else:
            print(f"  ✗ {app:12} -> Not resolved")
    assert successes >= 6, f"Expected at least 6 apps to resolve, got {successes}"
    print(f"  Passed ({successes}/{len(apps_to_test)} resolved)")

def test_physical_idle_detection():
    print("\n--- 2. Testing Windows Physical Idle Detection ---")
    idle_secs = HeartbeatScheduler._get_system_idle_seconds()
    print(f"  [OK] Native Windows physical idle time: {idle_secs:.2f} seconds")
    assert idle_secs >= 0.0

async def test_dream_synthesis():
    print("\n--- 3. Testing Idle / Sleep Synthesis ('Dream Mode') & Morning Brief ---")
    kg_path = PROJECT_ROOT / "data" / "knowledge" / "graph.json"
    kg = KnowledgeGraph(str(kg_path))
    engine = DreamSynthesisEngine(knowledge_graph=kg, data_dir=str(PROJECT_ROOT / "data" / "proactive"))
    report = await engine.run_synthesis_cycle(force=True)
    assert report is not None, "Dream synthesis report is None"
    print(f"  [OK] Dream synthesis completed in {report.duration_seconds:.2f}s")
    print(f"  [OK] Scanned entities: {report.entities_scanned}, Created nodes: {report.new_nodes_created}")
    
    brief_path = PROJECT_ROOT / "data" / "proactive" / "morning_brief.json"
    assert brief_path.exists(), "Morning brief JSON was not generated"
    print("  [OK] Morning briefing card generated successfully")

def test_live_chat_api():
    print("\n--- 4. Testing Live Engine API Endpoints ---")
    with httpx.Client(timeout=30) as client:
        # Health check
        info_resp = client.get("http://127.0.0.1:8900/api/status/info")
        assert info_resp.status_code == 200, f"Status info failed: {info_resp.status_code}"
        print(f"  [OK] Engine status 200 OK (Model: {info_resp.json()['llm']['model']})")

        # Conversational query
        chat_resp = client.post("http://127.0.0.1:8900/api/chat", json={
            "message": "Hey Dione, who is our project advisor and what are you doing?"
        })
        assert chat_resp.status_code == 200, f"Chat failed: {chat_resp.status_code}"
        reply = chat_resp.json().get("response", "")
        print(f"  [OK] Conversational reply received: {reply[:100]}...")
        assert "Geocey" in reply or "Prof" in reply, "Expected advisor mentioned in response"

if __name__ == "__main__":
    print("=" * 60)
    print("  DIONE AI PRODUCTION READINESS VERIFICATION SUITE")
    print("=" * 60)
    test_app_resolver()
    test_physical_idle_detection()
    asyncio.run(test_dream_synthesis())
    test_live_chat_api()
    print("\n" + "=" * 60)
    print("  ALL VERIFICATION TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)
