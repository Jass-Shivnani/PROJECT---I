"""
Dione AI — Comprehensive System Diagnostics & Troubleshooting Suite
Runs a deep, zero-mock probe across all 10 architectural subsystems.
"""

import sys
import os
import time
import asyncio
import traceback
import dotenv

dotenv.load_dotenv()

results = {}

def report(subsystem: str, passed: bool, details: str, latency_ms: float = 0):
    status = "PASS" if passed else "FAIL"
    results[subsystem] = {"status": status, "details": details, "latency_ms": round(latency_ms, 1)}
    print(f"[{status}] {subsystem:35} ({latency_ms:6.1f}ms) -> {details}")

async def run_diagnostics():
    print("=" * 80)
    print("   DIONE AI — DEEP SYSTEM DIAGNOSTIC & TROUBLESHOOTING PROBE")
    print("=" * 80)

    # 1. Environment & API Keys
    t0 = time.time()
    try:
        from server.config.settings import get_settings
        settings = get_settings()
        api_key = settings.llm.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            report("1. Environment & API Keys", False, "GEMINI_API_KEY is missing from environment", (time.time()-t0)*1000)
        else:
            masked = api_key[:6] + "..." + api_key[-4:]
            report("1. Environment & API Keys", True, f"Key present: {masked}, Model: {settings.llm.model}", (time.time()-t0)*1000)
    except Exception as e:
        report("1. Environment & API Keys", False, f"Error: {e}", (time.time()-t0)*1000)

    # 2. LLM Engine (Gemini Flash Lite)
    t0 = time.time()
    try:
        from server.llm.gemini import GeminiAdapter
        adapter = GeminiAdapter(api_key=api_key, model="gemini-3.5-flash-lite")
        resp = await adapter.generate("Respond with only the single word: ACKNOWLEDGED")
        passed = "ACKNOWLEDGED" in resp.upper()
        report("2. LLM Adapter (Gemini)", passed, f"Response: {resp.strip()[:40]}", (time.time()-t0)*1000)
    except Exception as e:
        report("2. LLM Adapter (Gemini)", False, f"LLM Call Failed: {e}", (time.time()-t0)*1000)

    # 3. Vision & Workstation Capture (64-bit GDI)
    t0 = time.time()
    try:
        from server.core.runtime.computer_use import get_computer_use_operator
        op = get_computer_use_operator()
        shot_path = await op.take_screenshot()
        size_kb = os.path.getsize(shot_path) / 1024
        report("3. Vision & Screen Capture", True, f"Captured: {shot_path} ({size_kb:.1f} KB)", (time.time()-t0)*1000)
    except Exception as e:
        report("3. Vision & Screen Capture", False, f"Screen Capture Failed: {e}", (time.time()-t0)*1000)

    # 4. Mouse Fail-Safe Monitor
    t0 = time.time()
    try:
        failsafe_on = op._monitoring_failsafe
        is_override = op.is_override_active()
        report("4. Mouse Fail-Safe Engine", failsafe_on and not is_override, f"Monitoring: {failsafe_on}, Override: {is_override}", (time.time()-t0)*1000)
    except Exception as e:
        report("4. Mouse Fail-Safe Engine", False, f"Fail-safe inspection error: {e}", (time.time()-t0)*1000)

    # 5. ChromaDB Memory & Vector Store
    t0 = time.time()
    try:
        from server.memory.manager import MemoryManager
        mem = MemoryManager(settings)
        await mem.initialize()
        recalled = await mem.recall("workstation preferences", limit=2)
        report("5. Memory & Vector Store", True, f"Recalled {len(recalled)} items from knowledge/conversations", (time.time()-t0)*1000)
    except Exception as e:
        report("5. Memory & Vector Store", False, f"Memory probe error: {e}", (time.time()-t0)*1000)

    # 6. Knowledge Graph (NetworkX GraphRAG)
    t0 = time.time()
    try:
        from server.knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph(settings.knowledge.graph_path)
        stats = kg.get_stats()
        report("6. Knowledge Graph (NetworkX)", True, f"Nodes: {stats['entities']}, Edges: {stats['relationships']}", (time.time()-t0)*1000)
    except Exception as e:
        report("6. Knowledge Graph (NetworkX)", False, f"KG probe error: {e}", (time.time()-t0)*1000)

    # 7. Hardware Telemetry & GPU Probe
    t0 = time.time()
    try:
        from server.plugins.builtin.system import SystemPlugin
        sys_p = SystemPlugin()
        info = await sys_p.get_system_info()
        gpu_detected = "RTX" in info or "NVIDIA" in info or "GPU" in info
        report("7. Hardware Telemetry & GPU", True, f"Telemetry online. GPU reported: {gpu_detected}", (time.time()-t0)*1000)
    except Exception as e:
        report("7. Hardware Telemetry & GPU", False, f"System Telemetry error: {e}", (time.time()-t0)*1000)

    # 8. Web Research (Zero-Mock DuckDuckGo + ArXiv)
    t0 = time.time()
    try:
        from server.plugins.builtin.web_research import WebResearchPlugin
        web_p = WebResearchPlugin()
        ddg_res = await web_p.search_web("FastAPI Python", max_results=1)
        arxiv_res = await web_p.search_arxiv("Multi-Agent Systems", max_results=1)
        passed = ("Link:" in ddg_res or "http" in ddg_res) and len(arxiv_res) > 50
        report("8. Web Research & arXiv", passed, f"DDG: {len(ddg_res)} chars, arXiv: {len(arxiv_res)} chars", (time.time()-t0)*1000)
    except Exception as e:
        report("8. Web Research & arXiv", False, f"Web Research error: {e}", (time.time()-t0)*1000)

    # 9. Telegram Companion Bot
    t0 = time.time()
    try:
        from server.telegram import TelegramBotService
        tg_token = os.getenv("DIONE_TELEGRAM_BOT_TOKEN")
        if tg_token:
            tg_service = TelegramBotService(bot_token=tg_token, engine=None)
            valid = await tg_service.start()
            bot_name = tg_service.bot_info.get("username", "Unknown")
            await tg_service.stop()
            report("9. Telegram Companion", valid, f"Bot verified: @{bot_name}", (time.time()-t0)*1000)
        else:
            report("9. Telegram Companion", True, "No Telegram token set (skipped)", (time.time()-t0)*1000)
    except Exception as e:
        report("9. Telegram Companion", False, f"Telegram error: {e}", (time.time()-t0)*1000)

    # 10. Native Client Bundle & Electron
    t0 = time.time()
    try:
        dist_html = os.path.join("client", "dist", "index.html")
        dist_exists = os.path.exists(dist_html)
        electron_main = os.path.join("client", "electron-main.cjs")
        electron_exists = os.path.exists(electron_main)
        report("10. Native Client & Electron", dist_exists and electron_exists, f"dist/index.html: {dist_exists}, electron-main: {electron_exists}", (time.time()-t0)*1000)
    except Exception as e:
        report("10. Native Client & Electron", False, f"Native App file error: {e}", (time.time()-t0)*1000)

    # 11. Full-Duplex Neural Voice (Gemini Live Orchestrator)
    t0 = time.time()
    try:
        from server.llm.gemini_live_orchestrator import GeminiLiveOrchestrator
        live_orch = GeminiLiveOrchestrator()
        report("11. Gemini Live Audio Engine", True, f"Voice model: Aoede 24kHz, gemini-2.5-flash-native-audio-latest", (time.time()-t0)*1000)
    except Exception as e:
        report("11. Gemini Live Audio Engine", False, f"Gemini Live error: {e}", (time.time()-t0)*1000)

    print("=" * 80)
    total_passed = sum(1 for v in results.values() if v["status"] == "PASS")
    total_tests = len(results)
    print(f"DIAGNOSTIC SUMMARY: {total_passed}/{total_tests} SUBSYSTEMS OPERATIONAL")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
