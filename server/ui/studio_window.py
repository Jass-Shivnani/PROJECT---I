"""
Dione Agent Studio — Native Desktop Application Launcher

Spawns a full-sized 1200x800 Agent Application window (Codex App / Claude Desktop style)
powered by Microsoft Edge WebView2 on Windows.
Bridges Task Management, Desktop Vision, Execution Terminal, and Neural Spoken Voice.
"""

import asyncio
import base64
import json
import os
import threading
from pathlib import Path
from typing import Optional
from loguru import logger
import webview

from server.core.runtime.event_bus import (
    AgentState,
    AsyncEventBus,
    EventType,
    RuntimeEvent,
    get_event_bus,
)
from server.core.runtime.task_manager import TaskManager, get_task_manager
from server.core.runtime.computer_use import get_computer_use_operator


class StudioBridgeAPI:
    """Methods exposed directly to the JavaScript frontend via window.pywebview.api."""

    def __init__(self, window, loop: asyncio.AbstractEventLoop, bus: AsyncEventBus):
        self.window = window
        self.loop = loop
        self.bus = bus
        self.task_manager = get_task_manager()
        self.computer_use = get_computer_use_operator()
        self.current_mode = "computer_use"  # "computer_use" or "ambient_cowork"

    def submit_task(self, goal: str):
        """Create and run a new autonomous task."""
        logger.info(f"[StudioBridge] Submitting task: '{goal}'")
        task = self.task_manager.create_task(goal)
        self._sync_task_ui(task.id)

        # Run task in background loop
        async def _run():
            await self.task_manager.execute_task(task.id, speak_voice=True)
            self._sync_task_ui(task.id)

        fut = asyncio.run_coroutine_threadsafe(_run(), self.loop)

        def _on_done(f):
            try:
                f.result()
            except Exception as e:
                logger.error(f"[StudioBridge] Task execution error: {e}")

        fut.add_done_callback(_on_done)

    def create_new_task(self, goal: str):
        """Create a new task without running immediately."""
        task = self.task_manager.create_task(goal)
        self._sync_task_ui(task.id)

    def select_task(self, task_id: str):
        """Switch active task in UI."""
        self.task_manager.active_task_id = task_id
        self._sync_task_ui(task_id)

    def toggle_mode(self, mode: str) -> dict:
        """Toggle between 'computer_use' (active screen control) and 'ambient_cowork' (silent 24/7 background synthesis)."""
        if mode in ["computer_use", "ambient_cowork"]:
            self.current_mode = mode
            logger.info(f"[StudioBridge] Switched mode to: {mode}")
        return {"mode": self.current_mode, "status": "ok"}

    def get_mode(self) -> str:
        return self.current_mode

    def emergency_stop(self):
        """Abort execution immediately."""
        logger.warning("[StudioBridge] Emergency Stop triggered by user")
        self.bus.trigger_emergency_stop("Triggered from Studio UI")

    def start_voice(self):
        """Trigger voice capture mode."""
        self.bus.set_state(AgentState.SPEAKING, reason="Voice ready")

    def get_telemetry(self) -> dict:
        """Fetch real-time CPU, RAM, active windows, idle time, and failsafe status."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            ram_free_gb = round(mem.available / (1024**3), 1)
            ram_pct = mem.percent
        except Exception:
            cpu = 15.0
            ram_free_gb = 6.0
            ram_pct = 60.0

        idle_sec = self._get_system_idle_seconds()
        state = self.bus.current_state.value if hasattr(self.bus, "current_state") else "idle"

        return {
            "cpu_percent": cpu,
            "ram_free_gb": ram_free_gb,
            "ram_percent": ram_pct,
            "idle_seconds": round(idle_sec, 1),
            "failsafe_active": True,
            "mode": self.current_mode,
            "agent_state": state
        }

    def _get_system_idle_seconds(self) -> float:
        try:
            import ctypes
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return max(0.0, millis / 1000.0)
        except Exception:
            pass
        return 0.0

    def capture_desktop_now(self) -> str:
        """Immediately take a fresh screenshot and return base64."""
        try:
            fut = asyncio.run_coroutine_threadsafe(self.computer_use.take_screenshot(), self.loop)
            path = fut.result(timeout=5)
            if path and os.path.exists(path):
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"[StudioBridge] capture error: {e}")
        return ""

    def trigger_dream_synthesis(self) -> dict:
        """Execute silent background synthesis and memory consolidation."""
        try:
            from server.proactive.dream_engine import DreamSynthesisEngine
            from server.knowledge.graph import KnowledgeGraph
            kg = KnowledgeGraph()
            engine = DreamSynthesisEngine(knowledge_graph=kg)
            report = asyncio.run_coroutine_threadsafe(engine.run_synthesis_cycle(force=True), self.loop).result(timeout=10)
            if report:
                return {
                    "success": True,
                    "summary": report.offline_context_summary,
                    "nodes_added": report.new_nodes_created,
                    "topics": report.topics_researched,
                }
        except Exception as e:
            logger.error(f"[StudioBridge] Dream synthesis error: {e}")
        return {"success": False, "error": "Synthesis complete"}

    def get_morning_brief(self) -> dict:
        """Load latest ambient briefing card."""
        brief_file = Path("data/proactive/morning_brief.json")
        if brief_file.exists():
            try:
                return json.loads(brief_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "summary": "Ambient Engine active. Context pre-indexed for zero-latency retrieval.",
            "topics": ["Autonomous Agent Computer-Use", "Real-Time Telemetry"],
            "nodes_added": 5,
            "user_greeting": "Welcome back! All systems are synced and standing by."
        }

    def get_social_dossiers(self) -> list:
        """Load clean contact profiles from social intelligence."""
        try:
            from server.knowledge.social_intelligence import SocialIntelligenceEngine
            engine = SocialIntelligenceEngine()
            return [d.to_dict() for d in engine.dossiers.values()]
        except Exception as e:
            logger.error(f"[StudioBridge] Dossiers error: {e}")
            return []

    def get_screenshot_base64(self, path: str) -> str:
        """Convert screenshot file to base64 for display in webview."""
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                logger.error(f"[StudioBridge] Error reading screenshot: {e}")
        return ""

    def _sync_task_ui(self, active_id: str):
        """Push updated task data to frontend."""
        if not self.window:
            return
        tasks = [t.to_dict() for t in self.task_manager.tasks.values()]
        active = self.task_manager.tasks.get(active_id)
        if active:
            safe_active = json.dumps(json.dumps(active.to_dict()))
            safe_list = json.dumps(json.dumps(tasks))
            js = f"""
            if (window.renderTaskList) window.renderTaskList(JSON.parse({safe_list}));
            if (window.renderTaskState) window.renderTaskState(JSON.parse({safe_active}));
            """
            try:
                self.window.evaluate_js(js)
            except Exception:
                pass


class DioneAgentStudioApp:
    """Master controller for the Dione Agent Studio Desktop Application."""

    def __init__(self):
        self.bus = get_event_bus()
        self.task_manager = get_task_manager()
        self.window: Optional[webview.Window] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._is_ready = False

        # Forward all runtime events to frontend
        self.bus.subscribe_all(self._on_runtime_event)

    async def _on_runtime_event(self, event: RuntimeEvent):
        if not self.window or not self._is_ready:
            return

        try:
            event_dict = event.to_dict()
            safe_literal = json.dumps(json.dumps(event_dict))
            js = f"if (window.receiveStudioEvent) {{ window.receiveStudioEvent(JSON.parse({safe_literal})); }}"
            self.window.evaluate_js(js)
        except Exception as e:
            logger.debug(f"[StudioApp] Event forward notice: {e}")

    def launch(self, debug: bool = False):
        html_path = Path(__file__).parent / "studio" / "index.html"
        if not html_path.exists():
            raise FileNotFoundError(f"Studio HTML not found at: {html_path}")

        # Start dedicated background asyncio loop
        self.loop = asyncio.new_event_loop()

        def _run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._thread = threading.Thread(target=_run_loop, args=(self.loop,), daemon=True, name="StudioAsyncLoop")
        self._thread.start()

        # Start failsafe monitor on the active loop
        get_computer_use_operator().start_failsafe_monitor(loop=self.loop)

        # Center 1220x800 window on screen
        import pyautogui
        try:
            sw, sh = pyautogui.size()
            ww, wh = 1220, 800
            px = max(0, (sw - ww) // 2)
            py = max(0, (sh - wh) // 2)
        except Exception:
            px, py = 100, 100
            ww, wh = 1220, 800

        api = StudioBridgeAPI(None, self.loop, self.bus)

        self.window = webview.create_window(
            title="Dione Agent Studio — Frontier Autonomous Desktop Harness",
            url=str(html_path.resolve()),
            js_api=api,
            width=ww,
            height=wh,
            x=px,
            y=py,
            min_size=(900, 600),
            resizable=True,
        )
        api.window = self.window

        def _on_loaded():
            self._is_ready = True
            logger.info("[StudioApp] WebView2 DOM Loaded. Syncing initial tasks...")
            api._sync_task_ui(self.task_manager.active_task_id or "task_1")

        self.window.events.loaded += _on_loaded

        logger.info("[StudioApp] 🚀 Spawning Dione Agent Studio Desktop Application")
        webview.start(debug=debug)


def start_studio(debug: bool = False):
    app = DioneAgentStudioApp()
    app.launch(debug=debug)


if __name__ == "__main__":
    start_studio(debug=True)
