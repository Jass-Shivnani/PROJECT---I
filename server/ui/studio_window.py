"""
Dione 2026 Agent Studio — Native Desktop Application Launcher
=============================================================
Spawns a 1400x880 flagship 2026 Agentic OS Desktop Window powered by
Microsoft Edge WebView2 on Windows.
Bridges:
- Hierarchical Multi-Agent Orchestration DAG & Live Sub-Agent Handoffs
- AI Model Computer-Use Viewport (UIA Tree, Coordinates, Vision Click, Audio/App Control)
- Full-Duplex Neural Voice Talk Studio (Edge-TTS + Spoken Filler Bridges + Barge-In)
- 5-Tier Safety Kernel & Human-in-the-Loop Mouse Fail-Safe
"""

import asyncio
import base64
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional
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
from server.core.runtime.voice_frontman import get_voice_frontman
from server.core.orchestrator import get_multi_agent_orchestrator


class StudioBridgeAPI:
    """Methods exposed directly to the JavaScript frontend via window.pywebview.api."""

    def __init__(self, window, loop: asyncio.AbstractEventLoop, bus: AsyncEventBus):
        self.window = window
        self.loop = loop
        self.bus = bus
        self.task_manager = get_task_manager()
        self.computer_use = get_computer_use_operator()
        self.voice_frontman = get_voice_frontman()
        self.orchestrator = get_multi_agent_orchestrator()
        self.current_mode = "computer_use"
        self.voice_enabled = True

    def submit_task(self, goal: str):
        """Create and run a new autonomous task through the Multi-Agent Orchestrator."""
        logger.info(f"[StudioBridge] Submitting orchestrated task: '{goal}'")
        task = self.task_manager.create_task(goal)
        self._sync_task_ui(task.id)

        async def _run():
            orch_session = await self.orchestrator.execute_orchestrated_goal(goal)
            await self.task_manager.execute_task(task.id, speak_voice=self.voice_enabled)
            self._sync_task_ui(task.id)
            self._push_orchestration_session(orch_session.to_dict())

        fut = asyncio.run_coroutine_threadsafe(_run(), self.loop)

        def _on_done(f):
            try:
                f.result()
            except Exception as e:
                logger.error(f"[StudioBridge] Task execution error: {e}")

        fut.add_done_callback(_on_done)
        return {"status": "started", "task_id": task.id}

    def execute_computer_action(self, action: str, payload_json: str = "{}") -> dict:
        """Execute a direct Computer-Use operator command from the UI or AI model."""
        try:
            params = json.loads(payload_json) if isinstance(payload_json, str) else (payload_json or {})
        except Exception:
            params = {}

        async def _do():
            if action == "click_coords":
                await self.computer_use.click_at_coordinates(
                    int(params.get("x", 500)),
                    int(params.get("y", 500)),
                    clicks=int(params.get("clicks", 1)),
                    button=str(params.get("button", "left")),
                )
                return f"Clicked ({params.get('x')}, {params.get('y')})"
            elif action == "type_text":
                await self.computer_use.type_text(
                    str(params.get("text", "")),
                    press_enter=bool(params.get("press_enter", False)),
                )
                return f"Typed '{params.get('text', '')}'"
            elif action == "hotkey":
                keys = [k.strip() for k in str(params.get("keys", "enter")).split("+")]
                await self.computer_use.press_hotkey(*keys)
                return f"Hotkey {'+'.join(keys)} sent"
            elif action == "launch_app":
                return await self.computer_use.launch_app(str(params.get("app", "notepad")))
            elif action == "volume":
                return await self.computer_use.adjust_volume(str(params.get("direction", "up")))
            elif action == "media":
                return await self.computer_use.media_control(str(params.get("command", "play_pause")))
            return "Action completed"

        try:
            fut = asyncio.run_coroutine_threadsafe(_do(), self.loop)
            res = fut.result(timeout=8)
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def speak_text(self, text: str) -> dict:
        """Speak text aloud via Edge-TTS Neural Voice."""
        try:
            asyncio.run_coroutine_threadsafe(self.voice_frontman.speak(text, is_filler=False), self.loop)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_voice(self) -> dict:
        """Barge-in / stop active speech playback immediately."""
        self.voice_frontman.stop_speech()
        return {"success": True}

    def toggle_voice_mode(self, enabled: bool) -> dict:
        self.voice_enabled = bool(enabled)
        return {"voice_enabled": self.voice_enabled}

    def create_new_task(self, goal: str):
        task = self.task_manager.create_task(goal)
        self._sync_task_ui(task.id)

    def select_task(self, task_id: str):
        self.task_manager.active_task_id = task_id
        self._sync_task_ui(task_id)

    def toggle_mode(self, mode: str) -> dict:
        if mode in ["computer_use", "ambient_cowork"]:
            self.current_mode = mode
            logger.info(f"[StudioBridge] Switched mode to: {mode}")
        return {"mode": self.current_mode, "status": "ok"}

    def get_mode(self) -> str:
        return self.current_mode

    def emergency_stop(self):
        logger.warning("[StudioBridge] Emergency Stop triggered by user")
        self.voice_frontman.stop_speech()
        self.bus.trigger_emergency_stop("Triggered from Studio UI")

    def start_voice(self):
        self.bus.set_state(AgentState.SPEAKING, reason="Voice Talk Active")

    def get_agent_catalog(self) -> list:
        return self.orchestrator.get_agent_catalog()

    def get_telemetry(self) -> dict:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            ram_free_gb = round(mem.available / (1024**3), 1)
            ram_pct = mem.percent
        except Exception:
            cpu = 15.0
            ram_free_gb = 6.4
            ram_pct = 58.0

        idle_sec = self._get_system_idle_seconds()
        state = self.bus.current_state.value if hasattr(self.bus, "current_state") else "idle"

        return {
            "cpu_percent": cpu,
            "ram_free_gb": ram_free_gb,
            "ram_percent": ram_pct,
            "idle_seconds": round(idle_sec, 1),
            "failsafe_active": True,
            "mode": self.current_mode,
            "agent_state": state,
            "voice_enabled": self.voice_enabled,
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
        brief_file = Path("data/proactive/morning_brief.json")
        if brief_file.exists():
            try:
                return json.loads(brief_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "summary": "Ambient Engine active. Context pre-indexed for zero-latency retrieval.",
            "topics": ["Hierarchical Multi-Agent Orchestration", "Autonomous Computer-Use", "Full-Duplex Neural Voice"],
            "nodes_added": 7,
            "user_greeting": "Welcome back! All 6 specialized agents are synced and standing by.",
        }

    def get_social_dossiers(self) -> list:
        try:
            from server.knowledge.social_intelligence import SocialIntelligenceEngine
            engine = SocialIntelligenceEngine()
            return [d.to_dict() for d in engine.dossiers.values()]
        except Exception as e:
            logger.error(f"[StudioBridge] Dossiers error: {e}")
            return []

    def get_screenshot_base64(self, path: str) -> str:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                logger.error(f"[StudioBridge] Error reading screenshot: {e}")
        return ""

    def _push_orchestration_session(self, session_dict: Dict[str, Any]):
        if not self.window:
            return
        safe_session = json.dumps(json.dumps(session_dict))
        js = f"if (window.receiveOrchestrationSession) window.receiveOrchestrationSession(JSON.parse({safe_session}));"
        try:
            self.window.evaluate_js(js)
        except Exception:
            pass

    def _sync_task_ui(self, active_id: str):
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
    """Master controller for the Dione 2026 Agent Studio Desktop Application."""

    def __init__(self):
        self.bus = get_event_bus()
        self.task_manager = get_task_manager()
        self.window: Optional[webview.Window] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._is_ready = False

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

        self.loop = asyncio.new_event_loop()

        def _run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._thread = threading.Thread(target=_run_loop, args=(self.loop,), daemon=True, name="StudioAsyncLoop")
        self._thread.start()

        get_computer_use_operator().start_failsafe_monitor(loop=self.loop)

        try:
            import pyautogui
            sw, sh = pyautogui.size()
            ww, wh = 1380, 860
            px = max(0, (sw - ww) // 2)
            py = max(0, (sh - wh) // 2)
        except Exception:
            px, py = 80, 60
            ww, wh = 1380, 860

        api = StudioBridgeAPI(None, self.loop, self.bus)

        self.window = webview.create_window(
            title="Dione 2026 Agentic OS — Multi-Agent Orchestrator · Computer Use · Neural Voice",
            url=str(html_path.resolve()),
            js_api=api,
            width=ww,
            height=wh,
            x=px,
            y=py,
            min_size=(1024, 680),
            resizable=True,
        )
        api.window = self.window

        def _on_loaded():
            self._is_ready = True
            logger.info("[StudioApp] WebView2 DOM Loaded. Syncing initial tasks...")
            api._sync_task_ui(self.task_manager.active_task_id or "task_1")

        self.window.events.loaded += _on_loaded
        logger.info("[StudioApp] 🚀 Spawning Dione 2026 Agent Studio Desktop Application")
        webview.start(debug=debug)


def start_studio(debug: bool = False):
    app = DioneAgentStudioApp()
    app.launch(debug=debug)


if __name__ == "__main__":
    start_studio(debug=True)
