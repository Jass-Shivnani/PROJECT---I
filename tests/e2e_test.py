"""
Dione AI -- End-to-End Integration Test
Run from project root: python tests/e2e_test.py
"""
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import json
import time

BASE = "http://127.0.0.1:8900"
PASSED = 0
FAILED = 0
RESULTS = []

def test(name, fn):
    global PASSED, FAILED
    try:
        result = fn()
        if result:
            PASSED += 1
            RESULTS.append(f"  [PASS] {name}")
            return True
        else:
            FAILED += 1
            RESULTS.append(f"  [FAIL] {name} - returned False")
            return False
    except Exception as e:
        FAILED += 1
        RESULTS.append(f"  [FAIL] {name} - {e}")
        return False

# ---- Test 1: Root endpoint ----
def test_root():
    r = httpx.get(f"{BASE}/", timeout=5)
    data = r.json()
    assert data["name"] == "Dione AI", f"Got {data['name']}"
    assert data["version"] == "0.2.0", f"Got {data['version']}"
    assert data["status"] == "alive"
    print(f"    Server: {data['name']} v{data['version']} ({data['status']})")
    return True

test("Root endpoint", test_root)

# ---- Test 2: Status info ----
def test_status_info():
    r = httpx.get(f"{BASE}/api/status/info", timeout=5)
    data = r.json()
    assert "version" in data
    assert "mood" in data
    assert "uptime" in data
    mood = data.get("mood", {})
    print(f"    Mood: {mood.get('label', '?')}, Uptime: {data['uptime']:.0f}s")
    return True

test("Status info", test_status_info)

# ---- Test 3: Heartbeat ----
def test_heartbeat():
    r = httpx.get(f"{BASE}/api/status/heartbeat", timeout=5)
    data = r.json()
    assert "activity_state" in data, f"Keys: {list(data.keys())}"
    assert "current_interval_seconds" in data
    print(f"    State: {data['activity_state']}, Interval: {data['current_interval_seconds']}s")
    return True

test("Heartbeat endpoint", test_heartbeat)

# ---- Test 4: Chat - real agent message ----
def test_chat():
    print("    Sending: 'Hello! What is your name?'")
    r = httpx.post(
        f"{BASE}/api/chat",
        json={"message": "Hello! What is your name?"},
        timeout=120,
    )
    assert r.status_code == 200, f"Status {r.status_code}"
    data = r.json()
    assert "response" in data, f"No 'response' key: {list(data.keys())}"
    resp_text = data["response"]
    assert len(resp_text) > 0, "Empty response"
    print(f"    Agent: {resp_text[:120]}{'...' if len(resp_text)>120 else ''}")
    if data.get("mood"):
        print(f"    Mood: {data['mood'].get('label', '?')}")
    print(f"    Latency: {data.get('latency_ms', 0):.0f}ms")
    if data.get("tools_used"):
        print(f"    Tools: {data['tools_used']}")
    return True

test("Chat agent (message 1)", test_chat)

# ---- Test 5: Chat follow-up ----
def test_chat2():
    print("    Sending: 'What can you help me with?'")
    r = httpx.post(
        f"{BASE}/api/chat",
        json={"message": "What can you help me with?"},
        timeout=120,
    )
    data = r.json()
    resp_text = data.get("response", "")
    assert len(resp_text) > 10, f"Too short: '{resp_text}'"
    print(f"    Agent: {resp_text[:120]}{'...' if len(resp_text)>120 else ''}")
    return True

test("Chat agent (message 2)", test_chat2)

# ---- Test 6: Setup module ----
def test_setup():
    from server.cli.setup import run_setup
    assert callable(run_setup)
    return True

test("Setup module import", test_setup)

# ---- Test 7: Settings module ----
def test_settings():
    from server.cli.settings_menu import run_settings
    assert callable(run_settings)
    return True

test("Settings module import", test_settings)

# ---- Test 8: Client module ----
def test_client():
    from server.cli.client import DioneClient, run_client
    assert callable(run_client)
    client = DioneClient("http://127.0.0.1:8900")
    assert client.server_url == "http://127.0.0.1:8900"
    return True

test("Client module import", test_client)

# ---- Test 9: Client can connect ----
def test_client_connect():
    import asyncio
    from server.cli.client import DioneClient
    client = DioneClient("http://127.0.0.1:8900")
    connected = asyncio.run(client.check_connection())
    assert connected, "Client could not connect"
    print(f"    Server info: {client.server_info.get('version', '?')}")
    return True

test("Client connects to server", test_client_connect)

# ---- Test 10: Client ping ----
def test_client_ping():
    import asyncio
    from server.cli.client import DioneClient
    client = DioneClient("http://127.0.0.1:8900")
    latency = asyncio.run(client.ping())
    assert latency >= 0, "Ping failed"
    print(f"    Ping: {latency:.0f}ms")
    return True

test("Client ping", test_client_ping)

# ---- Test 11: Profession knowledge ----
def test_profession():
    from server.knowledge.profession import ProfessionKnowledgeManager
    pm = ProfessionKnowledgeManager(data_dir="data")
    pm.set_profession("software")
    assert pm.profession == "software_engineer"
    assert pm.profile["name"] == "Software Engineer"
    # Test extraction
    entries = pm.extract_knowledge(
        "I am working on a Python REST API with FastAPI and I need to fix a bug in the database query layer",
        "user"
    )
    stats = pm.get_statistics()
    print(f"    Profession: {stats['profession']}")
    print(f"    Entries: {stats['total_entries']}, Extracted: {len(entries)}")
    return True

test("Profession knowledge", test_profession)

# ---- Test 12: Integrations ----
def test_integrations():
    from server.plugins.integrations import ALL_INTEGRATIONS
    count = len(ALL_INTEGRATIONS)
    assert count >= 7, f"Only {count} integrations"
    names = [cls().DISPLAY_NAME for cls in ALL_INTEGRATIONS]
    print(f"    {count} integrations: {', '.join(names)}")
    return True

test("Integrations loaded", test_integrations)

# ---- Test 13: Audio adapter ----
def test_audio():
    from server.llm.gemini_audio import GeminiAudioAdapter, AudioSession
    assert GeminiAudioAdapter.LIVE_MODEL == "gemini-2.0-flash-live-001"
    return True

test("Gemini Audio adapter", test_audio)

# ---- Test 14: Core engine ----
def test_engine():
    from server.core.engine import DioneEngine, EngineState
    assert EngineState.IDLE.value == "idle"
    return True

test("Core engine import", test_engine)

# ---- Test 15: Personality engine ----
def test_personality():
    from server.personality.engine import PersonalityEngine
    engine = PersonalityEngine()
    mood = engine.mood
    assert hasattr(mood, "label")
    print(f"    Default mood: {mood.label}")
    return True

test("Personality engine", test_personality)

# ---- Results ----
print()
print("=" * 55)
print(f"  RESULTS: {PASSED} passed, {FAILED} failed out of {PASSED+FAILED}")
print("=" * 55)
for r in RESULTS:
    print(r)
print()

if FAILED > 0:
    print("SOME TESTS FAILED - see above for details")
    sys.exit(1)
else:
    print("ALL TESTS PASSED!")
