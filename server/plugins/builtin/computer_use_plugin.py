"""
Dione AI — High-Speed Native Computer-Use & Vision Grounding Plugin (v3.0 Overhaul)
===================================================================================
Fixes all model schema, latency, and grounding bottlenecks:
1. Strongly-typed `computer_use` signature so Gemini's function-calling schema exposes
   `action`, `coordinate`, `element`, `text`, `keys`, `app`, `direction`, `amount`, and `duration`.
2. Zero Base64 Context Bloat: Screen captures publish images to the UI EventBus and save to
   `data/captures/latest_screen.jpg`, returning compact window + UIA control summaries to the LLM.
3. `inspect_screen_vision(question)`: Uses multimodal Gemini Vision (`Part.from_bytes`) to answer
   visual questions or read on-screen state without polluting the main chat context with base64.
4. `computer_locate_and_click(description)`: Performs recursive depth-6 Windows UIA tree search
   (<30ms) first, then falls back to Gemini Vision 0-1000 bounding-box grounding.
5. Instant Clipboard Typing (`computer_type`): Uses clipboard injection + Ctrl+V for fast, error-free
   text entry of URLs, emails, and messages.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from server.plugins.base import BasePlugin, dione_tool
from server.hermes_computer_use.tool import handle_computer_use
from server.hermes_computer_use.cua_backend import CuaDriverBackend
from server.core.runtime.event_bus import get_event_bus, RuntimeEvent, EventType

logger = logging.getLogger(__name__)

CHROME_EXE = Path(r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
EDGE_EXE = Path(r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe")
RIOT_EXE = Path(r"C:\\Riot Games\\Riot Client\\RiotClientServices.exe")


class ComputerUsePlugin(BasePlugin):
    """High-Speed Windows 11 Computer-Use, UIA & Multimodal Vision Plugin."""

    name = "ComputerUsePlugin"
    description = "Control the Windows 11 desktop: inspect screen with Vision/UIA, click elements or coordinates, type text, press shortcuts, launch apps, and play media."
    version = "3.0.0"

    def __init__(self):
        super().__init__()
        self._backend = CuaDriverBackend()
        self._captures_dir = Path("data/captures")
        self._captures_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Low-Level Win32 Primitives (Zero Latency)
    # ------------------------------------------------------------------

    def _bind_interactive_desktop(self):
        """Ensure thread is attached to interactive WinSta0/default desktop on Windows."""
        try:
            import ctypes
            if hasattr(ctypes, "windll"):
                u32 = ctypes.windll.user32
                hw = u32.OpenWindowStationW("WinSta0", False, 0xF037F)
                if hw:
                    u32.SetProcessWindowStation(hw)
                hd = u32.OpenDesktopW("default", 0, False, 0x01FF)
                if hd:
                    u32.SetThreadDesktop(hd)
        except Exception:
            pass

    def _send_native_win32_key(self, key_str: str) -> bool:
        """Direct Win32 keybd_event execution supporting combinations like ctrl+v, alt+tab, f11, enter."""
        import ctypes
        if not hasattr(ctypes, "windll"):
            return False
        user32 = ctypes.windll.user32
        KEYEVENTF_KEYUP = 0x0002

        VK_MAP = {
            "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
            "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
            "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B, "space": 0x20,
            "tab": 0x09, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
            "ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12,
            "win": 0x5B, "windows": 0x5B,
            "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
            "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
        }

        parts = [p.strip().lower() for p in re.split(r"[+\\-\\s]+", key_str) if p.strip()]
        vk_codes = []
        for p in parts:
            if p in VK_MAP:
                vk_codes.append(VK_MAP[p])
            elif len(p) == 1:
                vk = user32.VkKeyScanW(ord(p)) & 0xFF
                if vk > 0:
                    vk_codes.append(vk)

        if not vk_codes:
            return False

        for vk in vk_codes:
            user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.02)
        for vk in reversed(vk_codes):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        return True

    def _click_native_win32(self, x: int, y: int, double: bool = False, right: bool = False) -> bool:
        """Direct Win32 SetCursorPos + mouse_event execution."""
        import ctypes
        if not hasattr(ctypes, "windll"):
            return False
        user32 = ctypes.windll.user32
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010

        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.02)
        if right:
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            if double:
                time.sleep(0.04)
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return True

    def _list_native_win32_windows(self) -> List[Dict[str, Any]]:
        """Direct Win32 EnumWindows discovery with foreground flag."""
        import ctypes
        if not hasattr(ctypes, "windll"):
            return []
        user32 = ctypes.windll.user32
        fg_hwnd = user32.GetForegroundWindow()
        windows = []

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()
                    if title and title not in ("Program Manager", "Default IME", "MSCTFIME UI"):
                        pid = ctypes.c_ulong()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        windows.append({
                            "hwnd": hwnd,
                            "title": title,
                            "pid": pid.value,
                            "active": (hwnd == fg_hwnd),
                        })
            return True

        user32.EnumWindows.argtypes = None
        proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_cb)
        user32.EnumWindows(proc, 0)
        return windows

    def _focus_window_by_keyword(self, keyword: str) -> Optional[Dict[str, Any]]:
        """Bring a visible window matching keyword to foreground focus via Win32."""
        import ctypes
        if not hasattr(ctypes, "windll"):
            return None
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        kw_low = keyword.lower().strip()
        windows = self._list_native_win32_windows()
        target = next((w for w in windows if kw_low in w["title"].lower()), None)
        if not target:
            return None

        hwnd = target["hwnd"]
        try:
            user32.AllowSetForegroundWindow(-1)
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
            cur_thread = kernel32.GetCurrentThreadId()
            if fg_thread and fg_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, fg_thread, True)
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
                user32.AttachThreadInput(cur_thread, fg_thread, False)
            else:
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
        except Exception:
            pass
        return target

    def _extract_active_uia_elements(self, max_elements: int = 30) -> List[Dict[str, Any]]:
        """Fast recursive extraction of interactive UIA controls in the foreground window."""
        elements: List[Dict[str, Any]] = []
        try:
            import uiautomation as auto
            fg_ctrl = auto.GetForegroundControl()
            if not fg_ctrl:
                return elements

            interactive_types = {
                "ButtonControl", "EditControl", "HyperlinkControl",
                "TabItemControl", "MenuItemControl", "ComboBoxControl",
                "CheckBoxControl", "ListItemControl",
            }

            def _walk(ctrl, depth: int = 0):
                if depth > 5 or len(elements) >= max_elements:
                    return
                try:
                    c_type = ctrl.ControlTypeName
                    name = (ctrl.Name or "").strip()
                    if c_type in interactive_types and name and len(name) <= 80:
                        rect = ctrl.BoundingRectangle
                        if rect and rect.width() > 4 and rect.height() > 4:
                            cx = (rect.left + rect.right) // 2
                            cy = (rect.top + rect.bottom) // 2
                            if cx >= 0 and cy >= 0:
                                elements.append({
                                    "name": name,
                                    "type": c_type.replace("Control", ""),
                                    "center": [cx, cy],
                                })
                    for child in ctrl.GetChildren():
                        _walk(child, depth + 1)
                        if len(elements) >= max_elements:
                            break
                except Exception:
                    pass

            _walk(fg_ctrl, 0)
        except Exception:
            pass
        return elements

    async def _capture_frame_to_disk_and_ui(self) -> Dict[str, Any]:
        """Captures screen to disk + UI EventBus WITHOUT returning base64 into LLM text context."""
        self._bind_interactive_desktop()
        from PIL import ImageGrab

        img = ImageGrab.grab()
        w, h = img.size
        save_path = self._captures_dir / "latest_screen.jpg"
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        jpg_bytes = buf.getvalue()
        save_path.write_bytes(jpg_bytes)
        b64_str = base64.b64encode(jpg_bytes).decode("ascii")

        windows = self._list_native_win32_windows()
        active_win = next((win for win in windows if win.get("active")), windows[0] if windows else {"title": "Desktop", "hwnd": 0})

        try:
            await get_event_bus().publish(
                RuntimeEvent(
                    event_type=EventType.SCREENSHOT_CAPTURED,
                    sender="ComputerUsePlugin",
                    payload={
                        "screenshot_png_b64": b64_str,
                        "window_title": active_win.get("title", "Desktop"),
                        "hwnd": active_win.get("hwnd", 0),
                        "width": w,
                        "height": h,
                    },
                )
            )
        except Exception:
            pass

        uia_controls = self._extract_active_uia_elements(max_elements=25)
        return {
            "ok": True,
            "resolution": [w, h],
            "saved_path": str(save_path),
            "active_window": active_win.get("title", "Desktop"),
            "open_windows": [win["title"] for win in windows[:12]],
            "interactive_controls": uia_controls,
            "_raw_jpeg_bytes": jpg_bytes,
        }

    # ------------------------------------------------------------------
    # First-Class Agent Tools (Clean, Non-Overlapping, Strongly Typed)
    # ------------------------------------------------------------------

    @dione_tool(
        description=(
            "Observe the current desktop state: captures a fresh screenshot for the UI, returns the active foreground window, "
            "all open window titles, and the clickable UI controls (with exact [x, y] coordinates) in the active window. "
            "Call this FIRST before clicking or interacting with an application."
        ),
        permission_level="read",
        requires_confirmation=False,
    )
    async def capture_screen(self, app: Optional[str] = None) -> str:
        """Capture screen state and return compact window + clickable element map (zero base64 bloat)."""
        if app and app.strip():
            self._focus_window_by_keyword(app.strip())
            await asyncio.sleep(0.2)

        try:
            info = await self._capture_frame_to_disk_and_ui()
            info.pop("_raw_jpeg_bytes", None)
            return json.dumps(info, indent=2)
        except Exception as e:
            windows = self._list_native_win32_windows()
            return json.dumps({
                "ok": True,
                "note": f"GDI capture fallback ({e})",
                "open_windows": [w["title"] for w in windows[:12]],
            })

    @dione_tool(
        description=(
            "Analyze the live desktop screen using Gemini Vision to answer a specific visual question or read on-screen text/UI state "
            "(e.g. 'What video is currently playing?', 'What error message is on screen?', 'Where is the Submit button?')."
        ),
        permission_level="read",
        requires_confirmation=False,
    )
    async def inspect_screen_vision(self, question: str = "Describe what is currently visible on the active window and any key buttons or text.") -> str:
        """Multimodal Gemini Vision inspection of the live desktop screen without polluting chat context with base64."""
        try:
            info = await self._capture_frame_to_disk_and_ui()
            jpg_bytes = info.pop("_raw_jpeg_bytes", None)
            if not jpg_bytes:
                return f"Screen state: {json.dumps(info)}"

            api_key = os.getenv("DIONE_LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                return f"Screen state (no API key for vision): {json.dumps(info)}"

            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            w, h = info.get("resolution", [1920, 1080])
            prompt = (
                f"Screen Resolution: {w}x{h}. Active Window: {info.get('active_window')}.\\n"
                f"Question / Task: {question}\\n"
                f"Provide a concise, factual answer including approximate pixel coordinates [x, y] for any relevant buttons or UI elements."
            )

            for model_id in ["gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"]:
                try:
                    resp = await client.aio.models.generate_content(
                        model=model_id,
                        contents=[
                            types.Part.from_bytes(data=jpg_bytes, mime_type="image/jpeg"),
                            prompt,
                        ],
                        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=400),
                    )
                    if resp and resp.text:
                        return (
                            f"[Vision Analysis ({model_id}) | Active Window: {info.get('active_window')}]\\n"
                            f"{resp.text.strip()}"
                        )
                except Exception:
                    continue

            return json.dumps(info, indent=2)
        except Exception as e:
            return f"Vision inspection error: {e}"

    @dione_tool(
        description=(
            "Locate any button, link, tab, input box, or icon on the screen by its name or visual description "
            "(e.g. 'Search box', 'Play button', 'Send button', 'Compose') and click it automatically. "
            "Uses fast Windows UIA tree matching (<30ms) first, then Gemini Vision coordinate grounding."
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_locate_and_click(self, description: str, double: bool = False, right_click: bool = False) -> str:
        """Locate UI element via recursive UIA tree or Gemini Vision and click it."""
        desc_clean = description.strip()
        desc_low = desc_clean.lower()

        # 1. Fast recursive UIA lookup in foreground window
        uia_elements = self._extract_active_uia_elements(max_elements=60)
        best_match = None
        for el in uia_elements:
            el_name = el["name"].lower()
            if desc_low == el_name or desc_low in el_name or el_name in desc_low:
                best_match = el
                break

        if best_match:
            cx, cy = best_match["center"]
            self._click_native_win32(cx, cy, double=double, right=right_click)
            return f"Located '{best_match['name']}' ({best_match['type']}) via Windows UIA and clicked at ({cx}, {cy})."

        # 2. Multimodal Gemini Vision Grounding
        try:
            info = await self._capture_frame_to_disk_and_ui()
            jpg_bytes = info.pop("_raw_jpeg_bytes", None)
            sw, sh = info.get("resolution", [1920, 1080])

            api_key = os.getenv("DIONE_LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
            if jpg_bytes and api_key:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                v_prompt = (
                    f"Locate the UI element described as: \\\"{desc_clean}\\\" on this {sw}x{sh} screen.\\n"
                    f"Return ONLY a JSON object with 0-1000 normalized bounding box coordinates:\\n"
                    f'{{\"box_2d\": [ymin, xmin, ymax, xmax]}}'
                )
                for v_model in ["gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"]:
                    try:
                        resp = await client.aio.models.generate_content(
                            model=v_model,
                            contents=[
                                types.Part.from_bytes(data=jpg_bytes, mime_type="image/jpeg"),
                                v_prompt,
                            ],
                            config=types.GenerateContentConfig(
                                temperature=0.1,
                                response_mime_type="application/json",
                            ),
                        )
                        if resp and resp.text:
                            v_data = json.loads(resp.text)
                            if isinstance(v_data, list):
                                v_data = v_data[0] if v_data else {}
                            box = v_data.get("box_2d")
                            if box and len(box) == 4:
                                ymin, xmin, ymax, xmax = box
                                cx = int(((xmin + xmax) / 2.0) / 1000.0 * sw)
                                cy = int(((ymin + ymax) / 2.0) / 1000.0 * sh)
                                self._click_native_win32(cx, cy, double=double, right=right_click)
                                return f"Visually located '{desc_clean}' via {v_model} and clicked at pixel ({cx}, {cy})."
                    except Exception as ve:
                        logger.debug(f"[VisionClick] {v_model} note: {ve}")
                        continue
        except Exception as e:
            logger.error(f"[ComputerUse] Vision locate_and_click error: {e}")

        return (
            f"Could not locate '{desc_clean}' on active window. "
            f"Visible controls: {[e['name'] for e in uia_elements[:10]]}"
        )

    @dione_tool(
        description=(
            "Execute a low-level desktop action.\n"
            ":param action: One of 'click', 'double_click', 'right_click', 'type', 'key', 'scroll', 'wait', 'focus_app', 'list_windows', 'list_apps', 'capture'\n"
            ":param coordinate: [x, y] pixel coordinates for click actions\n"
            ":param element: UI element index if using Set-of-Mark\n"
            ":param text: Text string to type when action='type'\n"
            ":param keys: Key or shortcut to press when action='key' (e.g. 'enter', 'f11', 'ctrl+l', 'ctrl+t', 'alt+tab')\n"
            ":param app: Application name or window title for 'focus_app'\n"
            ":param direction: Scroll direction ('up', 'down', 'left', 'right')\n"
            ":param amount: Scroll ticks (default 5)\n"
            ":param duration: Wait duration in seconds when action='wait'"
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_use(
        self,
        action: str,
        coordinate: Optional[List[int]] = None,
        element: Optional[int] = None,
        text: Optional[str] = None,
        keys: Optional[str] = None,
        app: Optional[str] = None,
        mode: str = "som",
        direction: str = "down",
        amount: int = 5,
        duration: float = 1.0,
        delivery_mode: str = "foreground",
    ) -> str:
        """Strongly-typed unified computer_use action dispatcher with fast native Win32 execution."""
        act = (action or "").strip().lower()

        if act in ("capture", "screenshot"):
            return await self.capture_screen(app=app)

        if act in ("list_windows", "windows"):
            wins = self._list_native_win32_windows()
            return json.dumps({"ok": True, "count": len(wins), "windows": wins[:20]})

        if act == "focus_app" and app:
            matched = self._focus_window_by_keyword(app)
            if matched:
                return json.dumps({"ok": True, "action": "focus_app", "focused": matched["title"]})

        if act in ("click", "left_click", "double_click", "right_click") and coordinate and len(coordinate) >= 2:
            x, y = int(coordinate[0]), int(coordinate[1])
            ok = self._click_native_win32(x, y, double=(act == "double_click"), right=(act == "right_click"))
            return json.dumps({"ok": ok, "action": act, "coordinate": [x, y]})

        if act == "type" and text is not None:
            return await self.computer_type(text=text, press_enter=False)

        if act in ("key", "hotkey", "press_key") and keys:
            ok = self._send_native_win32_key(keys)
            return json.dumps({"ok": ok, "action": "key", "keys": keys})

        if act in ("wait", "sleep"):
            wait_s = max(0.1, min(float(duration or 1.0), 15.0))
            await asyncio.sleep(wait_s)
            return json.dumps({"ok": True, "action": "wait", "duration": wait_s})

        if act == "scroll":
            try:
                import pyautogui
                ticks = int(amount or 5) * (120 if direction in ("up", "right") else -120)
                pyautogui.scroll(ticks)
                return json.dumps({"ok": True, "action": "scroll", "direction": direction, "amount": amount})
            except Exception as se:
                return json.dumps({"ok": False, "error": str(se)})

        # Fallback to Hermes CUA driver for element-index clicks or list_apps
        payload: Dict[str, Any] = {"action": act, "mode": mode, "delivery_mode": delivery_mode}
        if coordinate is not None:
            payload["coordinate"] = coordinate
        if element is not None:
            payload["element"] = element
        if text is not None:
            payload["text"] = text
        if keys is not None:
            payload["keys"] = keys
        if app is not None:
            payload["app"] = app

        try:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, handle_computer_use, payload)
            res_str = json.dumps(res) if isinstance(res, dict) else str(res)
            from server.core.tool_truncator import truncate_tool_result_text
            return truncate_tool_result_text(res_str)
        except Exception as e:
            return json.dumps({"ok": False, "action": act, "error": str(e)})

    @dione_tool(
        description="Click at exact (x, y) desktop pixel coordinates with the mouse.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_click(self, x: int, y: int, button: str = "left", double: bool = False) -> str:
        """Click at exact desktop pixel coordinate."""
        right = (button.lower() == "right")
        self._click_native_win32(x, y, double=double, right=right)
        return f"Clicked mouse at ({x}, {y}) [button={button}, double={double}]"

    @dione_tool(
        description="Type text into the currently focused window or input field (uses fast clipboard injection for reliability). Set press_enter=True to submit.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_type(self, text: str, press_enter: bool = False) -> str:
        """Fast, reliable text entry via clipboard paste (Ctrl+V) with Win32 keystroke fallback."""
        if not text:
            if press_enter:
                self._send_native_win32_key("enter")
            return "Pressed Enter."

        pasted = False
        if len(text) > 2:
            try:
                import pyperclip
                pyperclip.copy(text)
                await asyncio.sleep(0.03)
                pasted = self._send_native_win32_key("ctrl+v")
                await asyncio.sleep(0.05)
            except Exception:
                pasted = False

        if not pasted:
            import ctypes
            if hasattr(ctypes, "windll"):
                user32 = ctypes.windll.user32
                for char in text:
                    vk = user32.VkKeyScanW(ord(char))
                    if vk != -1:
                        shift = (vk >> 8) & 1
                        key_code = vk & 0xFF
                        if shift:
                            user32.keybd_event(0x10, 0, 0, 0)
                        user32.keybd_event(key_code, 0, 0, 0)
                        time.sleep(0.005)
                        user32.keybd_event(key_code, 0, 2, 0)
                        if shift:
                            user32.keybd_event(0x10, 0, 2, 0)

        if press_enter:
            await asyncio.sleep(0.04)
            self._send_native_win32_key("enter")

        return f"Typed '{text[:80]}' into active window (press_enter={press_enter})."

    @dione_tool(
        description="Press a keyboard shortcut or hotkey: 'f' (YouTube fullscreen), 'f11' (browser fullscreen), 'ctrl+l' (address bar), 'ctrl+t' (new tab), 'ctrl+w' (close tab), 'alt+tab', 'enter', 'esc', 'space'.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_hotkey(self, keys: str) -> str:
        """Trigger keyboard shortcut directly via Win32."""
        ok = self._send_native_win32_key(keys)
        return f"Pressed hotkey '{keys}' (success={ok})."

    @dione_tool(
        description="Open Microsoft Edge or Google Chrome to a URL (automatically prepends https:// if needed).",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def open_browser(self, url: str = "https://www.google.com", browser: str = "auto", fullscreen: bool = False) -> str:
        """Open web browser to a URL and bring it to foreground focus."""
        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = f"https://{target_url}"

        b_choice = browser.lower()
        if b_choice in ("auto", "default"):
            b_choice = "chrome" if CHROME_EXE.exists() else "edge"

        fs_flag = "--start-fullscreen" if fullscreen else "--start-maximized"
        try:
            if "chrome" in b_choice and CHROME_EXE.exists():
                subprocess.Popen([str(CHROME_EXE), fs_flag, target_url])
                await asyncio.sleep(0.6)
                self._focus_window_by_keyword("chrome")
                return f"Opened Google Chrome to {target_url} (fullscreen={fullscreen})"
            elif "edge" in b_choice and EDGE_EXE.exists():
                subprocess.Popen([str(EDGE_EXE), fs_flag, target_url])
                await asyncio.sleep(0.6)
                self._focus_window_by_keyword("edge")
                return f"Opened Microsoft Edge to {target_url} (fullscreen={fullscreen})"
            else:
                webbrowser.open(target_url)
                return f"Opened default browser to {target_url}"
        except Exception as e:
            webbrowser.open(target_url)
            return f"Opened browser to {target_url} ({e})"

    @dione_tool(
        description="Play a YouTube video directly by query (resolves top video watch URL and opens it in full screen).",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def play_youtube_video(self, query: str, fullscreen: bool = True, browser: str = "auto") -> str:
        """Resolve top YouTube video watch URL and launch directly."""
        encoded = urllib.parse.quote_plus(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"
        watch_url = None

        try:
            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            loop = asyncio.get_running_loop()
            html = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=4.5).read().decode("utf-8", errors="ignore")
            )
            video_ids = re.findall(r"/watch\\?v=([a-zA-Z0-9_-]{11})", html) or re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
            if video_ids:
                watch_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
        except Exception as e:
            logger.debug(f"[YouTube] Direct ID lookup note: {e}")

        target_url = watch_url or search_url
        await self.open_browser(url=target_url, browser=browser, fullscreen=fullscreen)

        if fullscreen and watch_url:
            await asyncio.sleep(1.5)
            self._focus_window_by_keyword("youtube")
            self._send_native_win32_key("f")

        return f"Playing YouTube video '{query}' at {target_url} (fullscreen={fullscreen})."

    @dione_tool(
        description="Launch or focus a desktop application by name (e.g. 'Spotify', 'Chrome', 'Edge', 'VS Code', 'Notepad', 'Calculator', 'Explorer', 'Valorant').",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def launch_app(self, app: str) -> str:
        """Launch or focus desktop application."""
        a_lower = app.lower().strip()

        # First check if already open and focus it
        existing = self._focus_window_by_keyword(a_lower)
        if existing:
            return f"Focused already-running window: '{existing['title']}'."

        known_map = {
            "chrome": [str(CHROME_EXE)],
            "google chrome": [str(CHROME_EXE)],
            "edge": [str(EDGE_EXE)],
            "microsoft edge": [str(EDGE_EXE)],
            "riot client": [str(RIOT_EXE)],
            "valorant": [str(RIOT_EXE), "--launch-product=valorant", "--launch-patchline=live"],
            "notepad": ["notepad.exe"],
            "calc": ["calc.exe"],
            "calculator": ["calc.exe"],
            "explorer": ["explorer.exe"],
            "code": ["code"],
            "vs code": ["code"],
            "spotify": ["cmd", "/c", "start", "spotify:"],
        }

        cmd_args = known_map.get(a_lower)
        if cmd_args:
            try:
                subprocess.Popen(cmd_args, shell=(cmd_args[0] in ("cmd", "code")))
                await asyncio.sleep(0.8)
                self._focus_window_by_keyword(a_lower)
                return f"Launched and focused '{app}'."
            except Exception as e:
                logger.debug(f"Known app launch fallback: {e}")

        # Fallback to Windows start protocol or Hermes list_apps
        try:
            subprocess.Popen(f'start "" "{app}"', shell=True)
            await asyncio.sleep(0.8)
            return f"Launched application '{app}'."
        except Exception as e:
            return f"Could not launch '{app}': {e}"

    @dione_tool(
        description="List all visible open windows on the Windows desktop with their titles and active status.",
        permission_level="read",
        requires_confirmation=False,
    )
    async def list_open_windows(self) -> str:
        """List visible desktop windows."""
        wins = self._list_native_win32_windows()
        return json.dumps({"ok": True, "count": len(wins), "windows": wins[:25]}, indent=2)
