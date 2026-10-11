"""
Dione Next-Gen — PyWebView Native Dynamic Island Window

Spawns a frameless, transparent, always-on-top desktop companion
powered by Microsoft Edge WebView2 on Windows.
Bridges two-way events between JavaScript and the Tri-Actor Runtime.
"""

import asyncio
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
from server.core.runtime.voice_frontman import VoiceFrontman, get_voice_frontman
from server.core.runtime.cognitive_planner import CognitivePlanner, get_cognitive_planner
from server.core.runtime.computer_use import ComputerUseOperator, get_computer_use_operator


class OverlayBridgeAPI:
    """Methods exposed directly to the JavaScript frontend via window.pywebview.api."""

    def __init__(self, window, loop: asyncio.AbstractEventLoop, bus: AsyncEventBus):
        self.window = window
        self.loop = loop
        self.bus = bus
        self.frontman = get_voice_frontman()
        self.planner = get_cognitive_planner()
        self.operator = get_computer_use_operator()

    def set_window_size(self, width: int, height: int):
        """Resize the frameless desktop window smoothly and recenter."""
        try:
            import pyautogui
            screen_w, _ = pyautogui.size()
            new_x = max(0, (screen_w - width) // 2)
            self.window.move(new_x, 15)
            self.window.resize(width, height)
        except Exception as e:
            logger.error(f"[OverlayBridge] Failed to resize window: {e}")

    def emergency_stop(self):
        """Trigger instant system emergency stop."""
        logger.warning("[OverlayBridge] User pressed Emergency Stop button")
        self.bus.trigger_emergency_stop("Triggered from Dynamic Island UI")

    def submit_goal(self, goal: str):
        """Execute user goal through Voice Frontman + Cognitive Planner."""
        logger.info(f"[OverlayBridge] Goal submitted: '{goal}'")
        fut = asyncio.run_coroutine_threadsafe(
            self.frontman.bridge_and_execute(goal, self.planner.execute_goal(goal)),
            self.loop,
        )
        def _on_done(f):
            try:
                f.result()
            except Exception as e:
                logger.error(f"[OverlayBridge] Goal execution error: {e}")
        fut.add_done_callback(_on_done)

    def start_voice_capture(self):
        """Trigger voice capture mode."""
        logger.info("[OverlayBridge] Voice capture requested")
        self.bus.set_state(AgentState.LISTENING, reason="Listening to user voice")


class DynamicIslandOverlay:
    """Master controller for the Native Desktop Dynamic Island."""

    def __init__(self):
        self.bus = get_event_bus()
        self.window: Optional[webview.Window] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._is_ready = False

        # Subscribe to runtime events to stream to JS
        self.bus.subscribe_all(self._on_runtime_event)

    async def _on_runtime_event(self, event: RuntimeEvent):
        """Forward Python runtime events into WebView2 JavaScript."""
        if not self.window or not self._is_ready:
            return

        try:
            event_dict = event.to_dict()
            event_str = json.dumps(event_dict)
            safe_literal = json.dumps(event_str)
            js = f"if (window.receiveDioneEvent) {{ window.receiveDioneEvent(JSON.parse({safe_literal})); }}"
            self.window.evaluate_js(js)
        except Exception as e:
            logger.debug(f"[DynamicIsland] evaluate_js notice: {e}")

    def launch(self, debug: bool = False):
        """Launch the PyWebView window in a dedicated GUI thread."""
        html_path = Path(__file__).parent / "overlay" / "index.html"
        if not html_path.exists():
            raise FileNotFoundError(f"Dynamic Island HTML not found at: {html_path}")

        # Start a dedicated asyncio event loop in a background thread
        self.loop = asyncio.new_event_loop()

        def _run_async_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._thread = threading.Thread(target=_run_async_loop, args=(self.loop,), daemon=True, name="DioneAsyncLoop")
        self._thread.start()

        # Start computer-use failsafe monitor on the active loop
        get_computer_use_operator().start_failsafe_monitor(loop=self.loop)

        # Calculate centered position at top of primary screen
        import pyautogui
        try:
            screen_w, _ = pyautogui.size()
            win_w = 340
            win_h = 80
            pos_x = max(0, (screen_w - win_w) // 2)
            pos_y = 15
        except Exception:
            pos_x, pos_y = 500, 20
            win_w, win_h = 340, 80

        api = OverlayBridgeAPI(None, self.loop, self.bus)

        # Create frameless, transparent, on-top window
        self.window = webview.create_window(
            title="Dione AI Dynamic Island",
            url=str(html_path.resolve()),
            js_api=api,
            width=win_w,
            height=win_h,
            x=pos_x,
            y=pos_y,
            frameless=True,
            on_top=True,
            transparent=True,
            easy_drag=False,
            min_size=(280, 80),
        )
        api.window = self.window

        def _on_loaded():
            self._is_ready = True
            logger.info("[DynamicIsland] WebView2 DOM Loaded and Ready")

        self.window.events.loaded += _on_loaded

        logger.info("[DynamicIsland] 🚀 Spawning Native Dynamic Island Desktop Overlay")
        webview.start(debug=debug)


def start_overlay(debug: bool = False):
    overlay = DynamicIslandOverlay()
    overlay.launch(debug=debug)


if __name__ == "__main__":
    start_overlay(debug=True)
