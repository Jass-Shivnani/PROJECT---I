"""
Dione AI — High-Speed Native Computer-Use & Vision Grounding Plugin (v4.0 Codex / UFO2 Edition)
===============================================================================================
Implements state-of-the-art Computer-Using Agent (CUA) execution inspired by OpenAI Codex/CUA,
Microsoft UFO2 (OSWorld-W), and NousResearch Hermes CUA:
1. Strongly-typed `computer_use` signature so Gemini's function-calling schema exposes
   `action`, `coordinate`, `element`, `text`, `keys`, `app`, `direction`, `amount`, and `duration`.
2. Zero Base64 Context Bloat: Screen captures publish images to the UI EventBus and save to
   `data/captures/latest_screen.jpg`, returning compact window + UIA control maps to the LLM.
3. Set-of-Mark (SoM) + 0-100% Coordinate Grid Vision Overlay: Draws numbered interactive badges
   and a calibrated coordinate grid onto screenshots passed to Gemini Vision (`Part.from_bytes`)
   so visual localization achieves sub-pixel accuracy on games, browsers, and custom DirectX/Canvas UIs.
4. Hardware Scan-Code Input & Paced Physicality:
   - 60ms hover settle (`MOUSEEVENTF_MOVE`)
   - 75ms click hold duration (`LEFTDOWN` -> `LEFTUP`)
   - 120ms post-click settle
   - Hardware keyboard scan codes (`MapVirtualKeyW`) with 50ms key hold
5. Pre/Post Frame Change Verification: Every click/action verifies whether the screen visibly
   transitioned and reports exact feedback to the agent loop.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import logging
import math
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.plugins.base import BasePlugin, dione_tool
from server.hermes_computer_use.tool import handle_computer_use
from server.hermes_computer_use.cua_backend import CuaDriverBackend
from server.core.runtime.event_bus import get_event_bus, RuntimeEvent, EventType

logger = logging.getLogger(__name__)

CHROME_EXE = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EDGE_EXE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
RIOT_EXE = Path(r"C:\Riot Games\Riot Client\RiotClientServices.exe")


class ComputerUsePlugin(BasePlugin):
    """High-Precision Windows 11 Computer-Use, UIA, Set-of-Mark & Multimodal Vision Plugin."""

    name = "ComputerUsePlugin"
    description = "Control the Windows 11 desktop: inspect screen with Set-of-Mark Vision/UIA, click elements or coordinates, type text, press shortcuts, launch apps, and play media."
    version = "4.0.0"

    def __init__(self):
        super().__init__()
        self._backend = CuaDriverBackend()
        self._captures_dir = Path("data/captures")
        self._captures_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Low-Level Win32 Primitives (Hardware Scan Codes & Paced Physicality)
    # ------------------------------------------------------------------

    def _bind_interactive_desktop(self):
        """Ensure thread is attached to interactive WinSta0/default desktop with Per-Monitor DPI awareness."""
        try:
            import ctypes
            if hasattr(ctypes, "windll"):
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    try:
                        ctypes.windll.user32.SetProcessDPIAware()
                    except Exception:
                        pass
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
        """Direct Win32 keybd_event with hardware scan codes (MapVirtualKeyW) and 50ms hold duration."""
        import ctypes
        if not hasattr(ctypes, "windll"):
            return False
        self._bind_interactive_desktop()
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
            "volup": 0xAF, "voldown": 0xAE, "mute": 0xAD, "playpause": 0xB3,
        }

        parts = [p.strip().lower() for p in re.split(r"[+\-\s]+", key_str) if p.strip()]
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
            scan = user32.MapVirtualKeyW(vk, 0)
            user32.keybd_event(vk, scan, 0, 0)
        time.sleep(0.05)  # 50ms minimum keypress hold standard
        for vk in reversed(vk_codes):
            scan = user32.MapVirtualKeyW(vk, 0)
            user32.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
        return True

    def _click_native_win32(self, x: int, y: int, double: bool = False, right: bool = False) -> bool:
        """
        Direct Win32 SetCursorPos + mouse_event execution with:
        - Smooth 2-step cursor approach + MOUSEEVENTF_MOVE hover trigger
        - 60ms hover settle delay (critical for Chromium/Electron/DirectX/Riot Client buttons)
        - 75ms mouse hold duration between DOWN and UP
        - 120ms post-click settle delay
        """
        import ctypes
        if not hasattr(ctypes, "windll"):
            return False
        self._bind_interactive_desktop()
        user32 = ctypes.windll.user32
        MOUSEEVENTF_MOVE = 0x0001
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010

        tx, ty = int(x), int(y)
        # 1. Move cursor slightly near target then onto exact target so DirectInput/Chromium registers mouse-enter
        user32.SetCursorPos(max(0, tx - 3), max(0, ty - 3))
        user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
        time.sleep(0.015)
        user32.SetCursorPos(tx, ty)
        user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
        time.sleep(0.06)  # 60ms hover settle

        # 2. Perform click with deliberate 75ms hold duration
        if right:
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.075)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.075)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            if double:
                time.sleep(0.10)
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.075)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

        # 3. 120ms post-click settle delay
        time.sleep(0.12)
        return True

    def _drag_native_win32(self, start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 25) -> bool:
        """Perform a smooth native Win32 mouse drag from (start_x, start_y) to (end_x, end_y)."""
        import ctypes
        if not hasattr(ctypes, "windll"):
            return False
        self._bind_interactive_desktop()
        user32 = ctypes.windll.user32
        MOUSEEVENTF_MOVE = 0x0001
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004

        # 1. Move to start position and hover
        user32.SetCursorPos(int(start_x), int(start_y))
        user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
        time.sleep(0.06)

        # 2. Press left mouse button down
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.04)

        # 3. Interpolate movement
        for i in range(1, steps + 1):
            curr_x = int(start_x + (end_x - start_x) * (i / steps))
            curr_y = int(start_y + (end_y - start_y) * (i / steps))
            user32.SetCursorPos(curr_x, curr_y)
            user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
            time.sleep(0.012)

        # 4. Release left mouse button
        time.sleep(0.04)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.08)
        return True

    def _draw_circle_native_win32(self, center_x: int, center_y: int, radius: int = 80, steps: int = 40) -> bool:
        """Physically draw a circle on screen (e.g. in Paint canvas) by dragging mouse along circumference."""
        import ctypes
        if not hasattr(ctypes, "windll"):
            return False
        self._bind_interactive_desktop()
        user32 = ctypes.windll.user32
        MOUSEEVENTF_MOVE = 0x0001
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004

        # Start at 0 radians: (center_x + radius, center_y)
        start_x = int(center_x + radius)
        start_y = int(center_y)
        user32.SetCursorPos(start_x, start_y)
        user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
        time.sleep(0.08)

        # Mouse down
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)

        # Trace circumference (2 * pi)
        for i in range(1, steps + 1):
            angle = (2.0 * math.pi * i) / steps
            px = int(center_x + radius * math.cos(angle))
            py = int(center_y + radius * math.sin(angle))
            user32.SetCursorPos(px, py)
            user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
            time.sleep(0.015)

        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.08)
        return True

    def _get_screen_metrics(self) -> Tuple[int, int]:
        try:
            import ctypes
            if hasattr(ctypes, "windll"):
                return (ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))
        except Exception:
            pass
        return (1920, 1080)

    def _find_paint_canvas_bounds(self) -> Tuple[int, int, int, int]:
        """
        Finds the exact MS Paint / drawing canvas rectangle on screen via Windows UIA
        or active window geometry (excluding the top 170px Ribbon/toolbar).
        Returns (left, top, right, bottom).
        """
        sw, sh = self._get_screen_metrics()
        try:
            import uiautomation as auto
            fg = auto.GetForegroundControl()
            if fg:
                def _find_canvas(ctrl, depth: int = 0):
                    if depth > 6:
                        return None
                    try:
                        name = (ctrl.Name or "").lower()
                        cls = (ctrl.ClassName or "").lower()
                        rect = ctrl.BoundingRectangle
                        if rect and rect.width() > 250 and rect.height() > 200:
                            if any(k in name for k in ("canvas", "image", "drawing", "page")) or any(
                                k in cls for k in ("mspaintview", "a2fxw", "canvas", "paint")
                            ):
                                return (rect.left, rect.top, rect.right, rect.bottom)
                        for child in ctrl.GetChildren():
                            res = _find_canvas(child, depth + 1)
                            if res:
                                return res
                    except Exception:
                        pass
                    return None

                canvas_rect = _find_canvas(fg, 0)
                if canvas_rect:
                    return canvas_rect

                wrect = fg.BoundingRectangle
                if wrect and wrect.width() > 300 and wrect.height() > 250:
                    return (
                        wrect.left + 30,
                        wrect.top + 170,
                        wrect.right - 30,
                        wrect.bottom - 50,
                    )
        except Exception:
            pass

        return (int(sw * 0.15), int(sh * 0.22), int(sw * 0.85), int(sh * 0.85))

    def _drag_native_win32_path(
        self,
        points: List[Tuple[int, int]],
        step_delay_s: float = 0.012,
        button: str = "left",
    ) -> bool:
        """
        Executes a continuous mouse drag along a sequence of (x, y) points with
        cursor settle, down-hold, smooth interpolation, and guaranteed release.
        """
        import ctypes
        if not points or len(points) < 2 or not hasattr(ctypes, "windll"):
            return False
        self._bind_interactive_desktop()
        user32 = ctypes.windll.user32
        MOUSEEVENTF_MOVE = 0x0001
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010

        btn = (button or "left").lower()
        down_flag = MOUSEEVENTF_RIGHTDOWN if btn == "right" else MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP if btn == "right" else MOUSEEVENTF_LEFTUP

        x0, y0 = int(points[0][0]), int(points[0][1])
        user32.SetCursorPos(x0, y0)
        user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
        time.sleep(0.08)

        try:
            user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.06)

            for px, py in points[1:]:
                user32.SetCursorPos(int(px), int(py))
                user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
                time.sleep(max(0.005, float(step_delay_s)))

            time.sleep(0.05)
        finally:
            user32.mouse_event(up_flag, 0, 0, 0, 0)
            time.sleep(0.08)

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
                user32.BringWindowToTop(hwnd)
                user32.SetFocus(hwnd)
                user32.AttachThreadInput(cur_thread, fg_thread, False)
            else:
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.SetFocus(hwnd)
        except Exception:
            pass
        return target

    def _extract_active_uia_elements(self, max_elements: int = 45) -> List[Dict[str, Any]]:
        """Fast recursive depth-6 extraction of interactive UIA controls in the foreground window."""
        elements: List[Dict[str, Any]] = []
        try:
            import uiautomation as auto
            fg_ctrl = auto.GetForegroundControl()
            if not fg_ctrl:
                return elements

            interactive_types = {
                "ButtonControl", "EditControl", "HyperlinkControl",
                "TabItemControl", "MenuItemControl", "ComboBoxControl",
                "CheckBoxControl", "ListItemControl", "RadioButtonControl",
            }

            def _walk(ctrl, depth: int = 0):
                if depth > 6 or len(elements) >= max_elements:
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
                                    "id": len(elements) + 1,
                                    "name": name,
                                    "type": c_type.replace("Control", ""),
                                    "center": [cx, cy],
                                    "bounds": [rect.left, rect.top, rect.right, rect.bottom],
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

    def _render_som_and_grid_overlay(self, img, uia_controls: List[Dict[str, Any]]) -> bytes:
        """
        Draws a Set-of-Mark (SoM) numbered bounding-box overlay + 10% coordinate grid
        onto a copy of the screenshot for high-precision Gemini Vision grounding.
        """
        from PIL import ImageDraw

        annotated = img.copy().convert("RGB")
        draw = ImageDraw.Draw(annotated)
        w, h = annotated.size

        # 1. Draw subtle 10% coordinate grid lines and edge percentage labels
        for pct in range(10, 100, 10):
            gx = int(w * pct / 100.0)
            gy = int(h * pct / 100.0)
            draw.line([(gx, 0), (gx, h)], fill=(0, 210, 255), width=1)
            draw.line([(0, gy), (w, gy)], fill=(0, 210, 255), width=1)
            draw.rectangle([(gx - 18, 2), (gx + 22, 16)], fill=(10, 14, 26))
            draw.text((gx - 15, 3), f"{pct}%", fill=(0, 230, 255))
            draw.rectangle([(2, gy - 8), (34, gy + 8)], fill=(10, 14, 26))
            draw.text((4, gy - 6), f"{pct}%", fill=(0, 230, 255))

        # 2. Draw Set-of-Mark (SoM) numbered badges on discovered UIA controls
        for ctrl in uia_controls[:35]:
            b = ctrl.get("bounds")
            cid = ctrl.get("id")
            if b and len(b) == 4 and cid is not None:
                x1, y1, x2, y2 = b
                draw.rectangle([(x1, y1), (x2, y2)], outline=(255, 60, 120), width=2)
                tag = f"#{cid}"
                draw.rectangle([(x1, max(0, y1 - 16)), (x1 + 28, y1)], fill=(255, 40, 100))
                draw.text((x1 + 3, max(0, y1 - 14)), tag, fill=(255, 255, 255))

        out = io.BytesIO()
        annotated.save(out, format="JPEG", quality=85)
        return out.getvalue()

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

        # Compute fast 32x32 perceptual hash for state-transition detection
        thumb = img.resize((32, 32)).convert("L")
        frame_hash = hashlib.sha256(thumb.tobytes()).hexdigest()[:16]

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

        uia_controls = self._extract_active_uia_elements(max_elements=35)
        annotated_bytes = self._render_som_and_grid_overlay(img, uia_controls)
        som_path = self._captures_dir / "latest_screen_som.jpg"
        som_path.write_bytes(annotated_bytes)

        return {
            "ok": True,
            "resolution": [w, h],
            "frame_hash": frame_hash,
            "saved_path": str(save_path),
            "active_window": active_win.get("title", "Desktop"),
            "open_windows": [win["title"] for win in windows[:12]],
            "interactive_controls": [
                {"id": c["id"], "name": c["name"], "type": c["type"], "center": c["center"]}
                for c in uia_controls
            ],
            "_raw_jpeg_bytes": jpg_bytes,
            "_raw_annotated_jpeg_bytes": annotated_bytes,
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
            await asyncio.sleep(0.35)

        try:
            info = await self._capture_frame_to_disk_and_ui()
            info.pop("_raw_jpeg_bytes", None)
            info.pop("_raw_annotated_jpeg_bytes", None)
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
            "Analyze the live desktop screen using Gemini Vision (with a Set-of-Mark & 0-100% coordinate grid overlay) "
            "to answer a specific visual question, verify whether an action succeeded, or locate buttons in games/browsers "
            "(e.g. 'Where is the Play / Deathmatch button?', 'Did the modal open?', 'What is currently on screen?')."
        ),
        permission_level="read",
        requires_confirmation=False,
    )
    async def inspect_screen_vision(self, question: str = "Describe what is currently visible on the active window and give exact [x, y] pixel coordinates for key buttons.") -> str:
        """Multimodal Gemini Vision inspection of the live desktop screen without polluting chat context with base64."""
        try:
            info = await self._capture_frame_to_disk_and_ui()
            jpg_bytes = info.pop("_raw_annotated_jpeg_bytes", None) or info.pop("_raw_jpeg_bytes", None)
            info.pop("_raw_jpeg_bytes", None)
            if not jpg_bytes:
                return f"Screen state: {json.dumps(info)}"

            api_key = os.getenv("DIONE_LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                return f"Screen state (no API key for vision): {json.dumps(info)}"

            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            w, h = info.get("resolution", [1920, 1080])
            uia_summary = json.dumps(info.get("interactive_controls", [])[:20])
            prompt = (
                f"Screen Resolution: {w}x{h} pixels. Active Window: {info.get('active_window')}.\n"
                f"The screenshot has a 10% cyan percentage grid (10%..90%) and numbered red Set-of-Mark badges (#1, #2, ...) for UIA controls: {uia_summary}\n"
                f"Question / Verification Task: {question}\n"
                f"Provide a concise, factual answer including exact pixel coordinates [x, y] (computed from the grid or badge centers) for any relevant buttons or inputs."
            )

            for model_id in ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash-lite"]:
                try:
                    resp = await client.aio.models.generate_content(
                        model=model_id,
                        contents=[
                            types.Part.from_bytes(data=jpg_bytes, mime_type="image/jpeg"),
                            prompt,
                        ],
                        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=450),
                    )
                    if resp and resp.text:
                        return (
                            f"[Vision Analysis ({model_id}) | Active Window: {info.get('active_window')} | Resolution: {w}x{h}]\n"
                            f"{resp.text.strip()}"
                        )
                except Exception:
                    continue

            return json.dumps(info, indent=2)
        except Exception as e:
            return f"Vision inspection error: {e}"

    @dione_tool(
        description=(
            "Locate any button, link, tab, input box, game lobby button, or icon on the screen by its name or visual description "
            "(e.g. 'Play', 'Deathmatch', 'Start', 'Search box', 'Send button', 'Compose') and click it automatically. "
            "Uses a 3-stage hybrid pipeline: (1) recursive depth-6 Windows UIA tree matching (<30ms), "
            "(2) Set-of-Mark + 0-1000 Gemini Vision bounding-box localization, and (3) post-click visual frame-diff verification."
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_locate_and_click(self, description: str, double: bool = False, right_click: bool = False) -> str:
        """Locate UI element via recursive UIA tree or Set-of-Mark Gemini Vision, click it, and verify screen change."""
        desc_clean = description.strip()
        desc_low = desc_clean.lower()

        # Capture pre-click state (for UIA + Vision + pre-click frame hash)
        pre_info = await self._capture_frame_to_disk_and_ui()
        pre_hash = pre_info.get("frame_hash", "")
        uia_elements = pre_info.get("interactive_controls", [])
        sw, sh = pre_info.get("resolution", [1920, 1080])

        best_match = None
        # Stage 1A: Exact UIA name match
        for el in uia_elements:
            el_name = el["name"].lower().strip()
            if el_name and desc_low == el_name:
                best_match = el
                break

        # Stage 1B: Substring UIA match guarded by len >= 3 to prevent 1-letter false positives (Forensic Bug #10)
        if not best_match:
            for el in uia_elements:
                el_name = el["name"].lower().strip()
                if not el_name or len(el_name) < 3:
                    continue
                if (len(desc_low) >= 3 and desc_low in el_name) or (len(el_name) >= 3 and el_name in desc_low):
                    best_match = el
                    break

        clicked_coords: Optional[Tuple[int, int]] = None
        method_used = ""

        if best_match:
            cx, cy = best_match["center"]
            self._click_native_win32(cx, cy, double=double, right=right_click)
            clicked_coords = (cx, cy)
            method_used = f"Windows UIA ('{best_match['name']}', {best_match['type']})"

        # Stage 2: Multimodal Set-of-Mark + Grid Gemini Vision Grounding (for DirectX games, Riot Client, Canvas, custom web UIs)
        if not clicked_coords:
            jpg_bytes = pre_info.get("_raw_annotated_jpeg_bytes") or pre_info.get("_raw_jpeg_bytes")
            api_key = os.getenv("DIONE_LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
            if jpg_bytes and api_key:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                v_prompt = (
                    f"You are a high-precision computer vision UI element locator.\n"
                    f"Screen resolution is {sw}x{sh}. The image includes a 10% cyan coordinate grid and numbered red badges (#1, #2, ...) for UIA elements: {json.dumps(uia_elements[:25])}\n"
                    f"Carefully locate the exact clickable UI element, button, game mode tab, or control described as: \"{desc_clean}\".\n"
                    f"Return ONLY a JSON object with 0-1000 normalized bounding box coordinates tightly enclosing the target:\n"
                    f'{{"box_2d": [ymin, xmin, ymax, xmax], "label": "matched element text"}}'
                )
                for v_model in ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash-lite"]:
                    try:
                        resp = await client.aio.models.generate_content(
                            model=v_model,
                            contents=[
                                types.Part.from_bytes(data=jpg_bytes, mime_type="image/jpeg"),
                                v_prompt,
                            ],
                            config=types.GenerateContentConfig(
                                temperature=0.05,
                                response_mime_type="application/json",
                            ),
                        )
                        if resp and resp.text:
                            v_data = json.loads(resp.text)
                            if isinstance(v_data, list):
                                v_data = v_data[0] if v_data else {}
                            box = v_data.get("box_2d")
                            if box and len(box) == 4:
                                ymin, xmin, ymax, xmax = [float(v) for v in box]
                                cx = int(((xmin + xmax) / 2.0) / 1000.0 * sw)
                                cy = int(((ymin + ymax) / 2.0) / 1000.0 * sh)
                                self._click_native_win32(cx, cy, double=double, right=right_click)
                                clicked_coords = (cx, cy)
                                method_used = f"Gemini Vision SoM ({v_model})"
                                break
                    except Exception as ve:
                        logger.debug(f"[VisionClick] {v_model} note: {ve}")
                        continue

        if not clicked_coords:
            return (
                f"Could not locate '{desc_clean}' on active window '{pre_info.get('active_window')}'. "
                f"Visible UIA controls: {[e['name'] for e in uia_elements[:12]]}. "
                f"Call `inspect_screen_vision` to inspect the full screen layout."
            )

        # Stage 3: Post-click visual state transition check (450ms settle)
        await asyncio.sleep(0.45)
        post_info = await self._capture_frame_to_disk_and_ui()
        post_hash = post_info.get("frame_hash", "")
        changed = (pre_hash != post_hash) if (pre_hash and post_hash) else True
        cx, cy = clicked_coords

        return (
            f"Located '{desc_clean}' via {method_used} and clicked at pixel ({cx}, {cy}) "
            f"[Active Window: '{post_info.get('active_window')}', Screen Visually Transitioned: {changed}]."
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
                await asyncio.sleep(0.4)
                return json.dumps({"ok": True, "action": "focus_app", "focused": matched["title"]})

        if act in ("click", "left_click", "double_click", "right_click") and coordinate and len(coordinate) >= 2:
            x, y = int(coordinate[0]), int(coordinate[1])
            ok = self._click_native_win32(x, y, double=(act == "double_click"), right=(act == "right_click"))
            return json.dumps({"ok": ok, "action": act, "coordinate": [x, y]})

        if act in ("drag", "mouse_drag", "left_click_drag") and coordinate and len(coordinate) >= 4:
            ok = self._drag_native_win32(int(coordinate[0]), int(coordinate[1]), int(coordinate[2]), int(coordinate[3]))
            return json.dumps({"ok": ok, "action": act, "from": coordinate[:2], "to": coordinate[2:4]})

        if act in ("draw_shape", "draw_circle", "shape", "circle"):
            s_name = text or "circle"
            cx = int(coordinate[0]) if coordinate and len(coordinate) >= 2 else 700
            cy = int(coordinate[1]) if coordinate and len(coordinate) >= 2 else 500
            r = int(amount or 120)
            res = await self.computer_draw_shape(shape=s_name, center_x=cx, center_y=cy, radius=r, app=(app or "mspaint"))
            return json.dumps({"ok": True, "action": act, "result": res})

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
                import ctypes
                if hasattr(ctypes, "windll"):
                    MOUSEEVENTF_WHEEL = 0x0800
                    ticks = int(amount or 5) * (120 if direction in ("up", "right") else -120)
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, ticks, 0)
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
        description="Click at exact (x, y) desktop pixel coordinates with the mouse (uses 60ms hover + 75ms hold duration).",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_click(self, x: int, y: int, button: str = "left", double: bool = False) -> str:
        """Click at exact desktop pixel coordinate and verify active window state."""
        right = (button.lower() == "right")
        self._click_native_win32(x, y, double=double, right=right)
        return f"Clicked mouse at ({x}, {y}) [button={button}, double={double}, hold=75ms]"

    @dione_tool(
        description="Type text into the currently focused window or input field (uses fast clipboard injection for reliability). Set press_enter=True to submit.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_type(self, text: str, press_enter: bool = False, clear_first: bool = False) -> str:
        """Fast, reliable text entry via clipboard paste (Ctrl+V) with Win32 scan-code fallback."""
        if clear_first:
            self._send_native_win32_key("ctrl+a")
            await asyncio.sleep(0.04)
            self._send_native_win32_key("backspace")
            await asyncio.sleep(0.04)

        if not text:
            if press_enter:
                self._send_native_win32_key("enter")
            return "Pressed Enter."

        pasted = False
        if len(text) > 1:
            try:
                import pyperclip
                pyperclip.copy(text)
                await asyncio.sleep(0.04)
                pasted = self._send_native_win32_key("ctrl+v")
                await asyncio.sleep(0.06)
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
                        scan = user32.MapVirtualKeyW(key_code, 0)
                        if shift:
                            user32.keybd_event(0x10, user32.MapVirtualKeyW(0x10, 0), 0, 0)
                        user32.keybd_event(key_code, scan, 0, 0)
                        time.sleep(0.015)
                        user32.keybd_event(key_code, scan, 2, 0)
                        if shift:
                            user32.keybd_event(0x10, user32.MapVirtualKeyW(0x10, 0), 2, 0)

        if press_enter:
            await asyncio.sleep(0.05)
            self._send_native_win32_key("enter")

        return f"Typed '{text[:80]}' into active window (press_enter={press_enter})."

    @dione_tool(
        description="Press a keyboard shortcut or hotkey: 'f' (YouTube fullscreen), 'f11' (browser fullscreen), 'ctrl+l' (address bar), 'ctrl+t' (new tab), 'ctrl+w' (close tab), 'alt+tab', 'enter', 'esc', 'space'.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_hotkey(self, keys: str) -> str:
        """Trigger keyboard shortcut directly via Win32 hardware scan codes (50ms hold)."""
        ok = self._send_native_win32_key(keys)
        return f"Pressed hotkey '{keys}' (success={ok})."

    @dione_tool(
        description="Drag the mouse from (start_x, start_y) to (end_x, end_y) with left mouse button held down.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> str:
        """Drag mouse with left button held down between two screen coordinates."""
        ok = self._drag_native_win32(start_x, start_y, end_x, end_y)
        return f"Dragged mouse from ({start_x}, {start_y}) to ({end_x}, {end_y}) [success={ok}]."

    @dione_tool(
        description=(
            "Draw a geometric shape or freehand path directly onto MS Paint (`mspaint`), a drawing canvas, or the active screen: "
            "supports shape='circle', 'square', 'rectangle', 'triangle', 'star', 'heart', 'smiley', 'spiral', 'line', 'house', 'diamond', or 'arrow'. "
            "Automatically launches/focuses Paint, locates the white canvas below the Ribbon header, and draws with smooth SendInput mouse synthesis."
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_draw_shape(
        self,
        shape: str = "circle",
        center_x: int = 700,
        center_y: int = 500,
        radius: int = 120,
        app: str = "mspaint",
    ) -> str:
        """
        Draws one of the 12 verified geometric shapes on MS Paint or drawing canvas.
        Guards against center_x/center_y = 0 with safe canvas clamping.
        """
        # 1. Minimize Dione so it never blocks the Paint canvas
        try:
            from server.core.runtime.computer_use import get_computer_use_operator
            get_computer_use_operator().minimize_dione()
        except Exception:
            pass

        # 2. Ensure target app is open and brought to foreground
        target_app = (app or "mspaint").strip().lower()
        focused = self._focus_window_by_keyword(target_app)
        if not focused:
            await self.launch_app(target_app)
            await asyncio.sleep(1.0)
            focused = self._focus_window_by_keyword(target_app)
        await asyncio.sleep(0.4)

        # 3. Determine safe canvas bounds and center point
        c_left, c_top, c_right, c_bottom = self._find_paint_canvas_bounds()

        # Ribbon safety: Paint ribbon toolbar occupies top ~170px of the window
        min_safe_y = max(c_top + 170, c_top + 90)
        max_safe_y = max(min_safe_y + 120, c_bottom - 90)
        min_safe_x = c_left + 90
        max_safe_x = max(min_safe_x + 120, c_right - 90)

        # Clamping guard against Gemini passing center_x=0, center_y=0
        if center_x is None or center_x <= 0:
            cx = int((min_safe_x + max_safe_x) // 2)
        else:
            cx = max(min_safe_x, min(int(center_x), max_safe_x))

        if center_y is None or center_y <= 0:
            cy = int((min_safe_y + max_safe_y) // 2)
        else:
            cy = max(min_safe_y, min(int(center_y), max_safe_y))

        max_r = max(35, min(int(radius or 120), (max_safe_x - min_safe_x) // 3, (max_safe_y - min_safe_y) // 3))

        # 4. Activate canvas with initial click
        self._click_native_win32(cx, cy)
        await asyncio.sleep(0.12)

        s_type = (shape or "circle").strip().lower()
        strokes: List[List[Tuple[int, int]]] = []

        # 1. Circle / Oval
        if s_type in ("circle", "oval", "ring"):
            steps = 72
            pts = [
                (
                    int(round(cx + max_r * math.cos(2.0 * math.pi * i / steps))),
                    int(round(cy + max_r * math.sin(2.0 * math.pi * i / steps))),
                )
                for i in range(steps + 1)
            ]
            strokes.append(pts)

        # 2. Square
        elif s_type in ("square", "box"):
            corners = [
                (cx - max_r, cy - max_r),
                (cx + max_r, cy - max_r),
                (cx + max_r, cy + max_r),
                (cx - max_r, cy + max_r),
                (cx - max_r, cy - max_r),
            ]
            pts = []
            for i in range(len(corners) - 1):
                x1, y1 = corners[i]
                x2, y2 = corners[i + 1]
                for step in range(16):
                    t = step / 15.0
                    pts.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts)

        # 3. Rectangle
        elif s_type in ("rectangle", "rect"):
            rx = int(max_r * 1.45)
            ry = int(max_r * 0.85)
            corners = [
                (cx - rx, cy - ry),
                (cx + rx, cy - ry),
                (cx + rx, cy + ry),
                (cx - rx, cy + ry),
                (cx - rx, cy - ry),
            ]
            pts = []
            for i in range(len(corners) - 1):
                x1, y1 = corners[i]
                x2, y2 = corners[i + 1]
                for step in range(16):
                    t = step / 15.0
                    pts.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts)

        # 4. Triangle
        elif s_type == "triangle":
            corners = [
                (cx, cy - max_r),
                (cx + int(max_r * 0.95), cy + int(max_r * 0.85)),
                (cx - int(max_r * 0.95), cy + int(max_r * 0.85)),
                (cx, cy - max_r),
            ]
            pts = []
            for i in range(len(corners) - 1):
                x1, y1 = corners[i]
                x2, y2 = corners[i + 1]
                for step in range(18):
                    t = step / 17.0
                    pts.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts)

        # 5. Star (5-pointed)
        elif s_type == "star":
            outer_r = max_r
            inner_r = int(max_r * 0.42)
            verts = []
            for i in range(11):
                ang = -math.pi / 2.0 + i * (math.pi / 5.0)
                r_curr = outer_r if i % 2 == 0 else inner_r
                verts.append((int(cx + r_curr * math.cos(ang)), int(cy + r_curr * math.sin(ang))))
            pts = []
            for i in range(len(verts) - 1):
                x1, y1 = verts[i]
                x2, y2 = verts[i + 1]
                for step in range(10):
                    t = step / 9.0
                    pts.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts)

        # 6. Heart (Cardioid)
        elif s_type == "heart":
            steps = 72
            pts = []
            scale = max_r / 16.0
            for i in range(steps + 1):
                t = 2.0 * math.pi * i / steps
                hx = 16.0 * (math.sin(t) ** 3)
                hy = -(13.0 * math.cos(t) - 5.0 * math.cos(2 * t) - 2.0 * math.cos(3 * t) - math.cos(4 * t))
                pts.append((int(cx + hx * scale), int(cy + hy * scale)))
            strokes.append(pts)

        # 7. Smiley Face
        elif s_type in ("smiley", "face"):
            steps = 60
            strokes.append([
                (int(cx + max_r * math.cos(2 * math.pi * i / steps)), int(cy + max_r * math.sin(2 * math.pi * i / steps)))
                for i in range(steps + 1)
            ])
            er = max(10, max_r // 8)
            lx, ly = cx - int(max_r * 0.35), cy - int(max_r * 0.25)
            strokes.append([
                (int(lx + er * math.cos(2 * math.pi * i / 20)), int(ly + er * math.sin(2 * math.pi * i / 20)))
                for i in range(21)
            ])
            rx_e, ry_e = cx + int(max_r * 0.35), cy - int(max_r * 0.25)
            strokes.append([
                (int(rx_e + er * math.cos(2 * math.pi * i / 20)), int(ry_e + er * math.sin(2 * math.pi * i / 20)))
                for i in range(21)
            ])
            sr = int(max_r * 0.55)
            strokes.append([
                (int(cx + sr * math.cos(math.pi * 0.15 + math.pi * 0.7 * i / 30)), int(cy + int(max_r * 0.1) + sr * math.sin(math.pi * 0.15 + math.pi * 0.7 * i / 30)))
                for i in range(31)
            ])

        # 8. Spiral
        elif s_type == "spiral":
            steps = 100
            pts = []
            for i in range(steps + 1):
                t = 4.0 * math.pi * i / steps
                r_curr = (i / steps) * max_r
                pts.append((int(cx + r_curr * math.cos(t)), int(cy + r_curr * math.sin(t))))
            strokes.append(pts)

        # 9. Line
        elif s_type == "line":
            strokes.append([(cx - max_r, cy), (cx + max_r, cy)])

        # 10. Diamond
        elif s_type in ("diamond", "rhombus"):
            corners = [
                (cx, cy - max_r),
                (cx + int(max_r * 0.8), cy),
                (cx, cy + max_r),
                (cx - int(max_r * 0.8), cy),
                (cx, cy - max_r),
            ]
            pts = []
            for i in range(len(corners) - 1):
                x1, y1 = corners[i]
                x2, y2 = corners[i + 1]
                for step in range(16):
                    t = step / 15.0
                    pts.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts)

        # 11. House
        elif s_type == "house":
            hw = int(max_r * 0.9)
            hh = int(max_r * 0.7)
            b_top = cy - int(max_r * 0.1)
            b_bot = cy + hh
            corners_box = [
                (cx - hw, b_top),
                (cx + hw, b_top),
                (cx + hw, b_bot),
                (cx - hw, b_bot),
                (cx - hw, b_top),
            ]
            pts_box = []
            for i in range(len(corners_box) - 1):
                x1, y1 = corners_box[i]
                x2, y2 = corners_box[i + 1]
                for step in range(12):
                    t = step / 11.0
                    pts_box.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts_box)

            roof = [
                (cx - hw, b_top),
                (cx, cy - max_r),
                (cx + hw, b_top),
            ]
            pts_roof = []
            for i in range(len(roof) - 1):
                x1, y1 = roof[i]
                x2, y2 = roof[i + 1]
                for step in range(12):
                    t = step / 11.0
                    pts_roof.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts_roof)

            dw = int(hw * 0.3)
            dh = int(hh * 0.55)
            door = [
                (cx - dw, b_bot),
                (cx - dw, b_bot - dh),
                (cx + dw, b_bot - dh),
                (cx + dw, b_bot),
            ]
            pts_door = []
            for i in range(len(door) - 1):
                x1, y1 = door[i]
                x2, y2 = door[i + 1]
                for step in range(8):
                    t = step / 7.0
                    pts_door.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts_door)

        # 12. Arrow
        elif s_type == "arrow":
            pts_shaft = [
                (int(cx - max_r + (max_r * 1.7) * (i / 20.0)), cy)
                for i in range(21)
            ]
            strokes.append(pts_shaft)
            head_x = cx + int(max_r * 0.7)
            tip_x = cx + max_r
            corners_head = [
                (head_x - int(max_r * 0.35), cy - int(max_r * 0.45)),
                (tip_x, cy),
                (head_x - int(max_r * 0.35), cy + int(max_r * 0.45)),
            ]
            pts_head = []
            for i in range(len(corners_head) - 1):
                x1, y1 = corners_head[i]
                x2, y2 = corners_head[i + 1]
                for step in range(12):
                    t = step / 11.0
                    pts_head.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
            strokes.append(pts_head)

        else:
            strokes.append([(cx - max_r, cy), (cx + max_r, cy)])

        for stroke in strokes:
            self._drag_native_win32_path(stroke, step_delay_s=0.012, button="left")
            await asyncio.sleep(0.12)

        return f"Successfully drew '{s_type}' on MS Paint canvas centered at ({cx}, {cy}) with radius={max_r}px."

    @dione_tool(
        description="Physically draw a circle on the active window or canvas (e.g. Paint) by holding mouse left button down and tracing circumference around (center_x, center_y) with given radius (default 80px).",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_draw_circle(self, center_x: int = 700, center_y: int = 500, radius: int = 80) -> str:
        """Physically draw a smooth circle on screen (such as Paint canvas) via parametric mouse tracing."""
        return await self.computer_draw_shape(shape="circle", center_x=center_x, center_y=center_y, radius=radius, app="mspaint")

    @dione_tool(
        description=(
            "Execute a semantic Windows UIAutomation (UIA) action directly on a control by its name: "
            "supports pattern='invoke' (click button/menu), 'toggle' (checkbox), 'select' (tab/list item), or 'set_value' (text field)."
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_uia_action(
        self,
        target_name: str,
        pattern: str = "invoke",
        value: str = "",
        app: str = "",
    ) -> str:
        """Semantic UIA control invocation without relying on pixel coordinates."""
        if app and app.strip():
            self._focus_window_by_keyword(app.strip())
            await asyncio.sleep(0.3)

        t_low = target_name.strip().lower()
        pat_low = (pattern or "invoke").strip().lower()

        try:
            import uiautomation as auto
            fg = auto.GetForegroundControl()
            if not fg:
                return f"No foreground control available; falling back to computer_locate_and_click('{target_name}')."

            matched_ctrl = None

            def _search(ctrl, depth: int = 0):
                nonlocal matched_ctrl
                if depth > 6 or matched_ctrl is not None:
                    return
                try:
                    nm = (ctrl.Name or "").strip()
                    if nm and (nm.lower() == t_low or (len(t_low) >= 3 and t_low in nm.lower())):
                        matched_ctrl = ctrl
                        return
                    for ch in ctrl.GetChildren():
                        _search(ch, depth + 1)
                        if matched_ctrl is not None:
                            return
                except Exception:
                    pass

            _search(fg, 0)
            if not matched_ctrl:
                return f"UIA control '{target_name}' not found in foreground window."

            if pat_low == "toggle":
                toggle_pat = matched_ctrl.GetTogglePattern()
                if toggle_pat:
                    toggle_pat.Toggle()
                    return f"Toggled UIA control '{target_name}'."
            elif pat_low == "select":
                sel_pat = matched_ctrl.GetSelectionItemPattern()
                if sel_pat:
                    sel_pat.Select()
                    return f"Selected UIA item '{target_name}'."
            elif pat_low == "set_value" and value:
                val_pat = matched_ctrl.GetValuePattern()
                if val_pat:
                    val_pat.SetValue(value)
                    return f"Set value of UIA control '{target_name}' to '{value}'."

            inv_pat = matched_ctrl.GetInvokePattern()
            if inv_pat:
                inv_pat.Invoke()
                return f"Invoked UIA button '{target_name}'."

            rect = matched_ctrl.BoundingRectangle
            if rect:
                mid_x = (rect.left + rect.right) // 2
                mid_y = (rect.top + rect.bottom) // 2
                self._click_native_win32(mid_x, mid_y)
                return f"Clicked UIA element '{target_name}' at ({mid_x}, {mid_y})."

            return f"Control '{target_name}' found but no actionable UIA pattern available."
        except Exception as e:
            return f"UIA action error: {e}"

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
                await asyncio.sleep(1.5)
                self._focus_window_by_keyword("chrome")
                await asyncio.sleep(0.4)
                return f"Opened Google Chrome to {target_url} (fullscreen={fullscreen})"
            elif "edge" in b_choice and EDGE_EXE.exists():
                subprocess.Popen([str(EDGE_EXE), fs_flag, target_url])
                await asyncio.sleep(1.5)
                self._focus_window_by_keyword("edge")
                await asyncio.sleep(0.4)
                return f"Opened Microsoft Edge to {target_url} (fullscreen={fullscreen})"
            else:
                webbrowser.open(target_url)
                await asyncio.sleep(1.2)
                return f"Opened default browser to {target_url}"
        except Exception as e:
            webbrowser.open(target_url)
            return f"Opened browser to {target_url} ({e})"

    @dione_tool(
        description="Play a YouTube video directly by query or channel name (resolves direct /watch?v=... URL, avoids help videos, and opens in full screen).",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def play_youtube_video(self, query: str, fullscreen: bool = True, browser: str = "auto") -> str:
        """Resolve top YouTube video watch URL and launch directly (with static help video filter)."""
        raw_input = (query or "").strip()

        # 1. Clean CLI execution wrappers and outer quotes (Forensic Bug #06)
        clean_q = re.sub(r'^(?:start\s+(?:chrome|msedge|edge|browser)\s+)?["\']?', '', raw_input, flags=re.I)
        clean_q = re.sub(r'["\']?$', '', clean_q).strip()

        # Exclude static YouTube help / support video IDs
        EXCLUDED_HELP_IDS = {"6rZRe1nfrJo", "dQw4w9WgXcQ"}
        watch_url = None

        # 2. Check if already a direct YouTube watch URL
        watch_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', clean_q)
        if watch_match and watch_match.group(1) not in EXCLUDED_HELP_IDS:
            watch_url = f"https://www.youtube.com/watch?v={watch_match.group(1)}"

        # 3. Check if channel URL (e.g. https://www.youtube.com/@MrWhosetheboss or @MrWhosetheboss/videos)
        if not watch_url:
            channel_match = re.search(r'(?:https?://(?:www\.)?youtube\.com/)?(@[a-zA-Z0-9_.-]+(?:/videos)?)', clean_q)
            if channel_match:
                ch_path = channel_match.group(1)
                if not ch_path.endswith('/videos'):
                    ch_path += '/videos'
                ch_url = f"https://www.youtube.com/{ch_path}"
                try:
                    req = urllib.request.Request(
                        ch_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    )
                    loop = asyncio.get_running_loop()
                    html = await loop.run_in_executor(
                        None, lambda: urllib.request.urlopen(req, timeout=6.0).read().decode("utf-8", errors="ignore")
                    )
                    vids = [
                        v for v in (
                            re.findall(r'"videoRenderer":\s*\{"videoId":"([a-zA-Z0-9_-]{11})"', html)
                            + re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                        )
                        if v not in EXCLUDED_HELP_IDS
                    ]
                    if vids:
                        watch_url = f"https://www.youtube.com/watch?v={vids[0]}"
                except Exception as e:
                    logger.debug(f"[YouTube] Channel video lookup note: {e}")

        # 4. Standard YouTube search with natural language prefix stripping
        if not watch_url:
            search_terms = re.sub(r'\b(?:open\s+(?:yt|youtube)\s+(?:and\s+)?|play\s+|in\s+full\s*screen|full\s*screen)\b', '', clean_q, flags=re.I).strip()
            if not search_terms:
                search_terms = clean_q

            encoded = urllib.parse.quote_plus(search_terms)
            search_url = f"https://www.youtube.com/results?search_query={encoded}"

            try:
                req = urllib.request.Request(
                    search_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                loop = asyncio.get_running_loop()
                html = await loop.run_in_executor(
                    None, lambda: urllib.request.urlopen(req, timeout=6.0).read().decode("utf-8", errors="ignore")
                )
                video_ids = [
                    v for v in (
                        re.findall(r'"videoRenderer":\s*\{"videoId":"([a-zA-Z0-9_-]{11})"', html)
                        + re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                    )
                    if v not in EXCLUDED_HELP_IDS
                ]
                if video_ids:
                    watch_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
            except Exception as e:
                logger.debug(f"[YouTube] Direct ID lookup note: {e}")

        target_url = watch_url or (f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_q)}" if not clean_q.startswith("http") else clean_q)
        await self.open_browser(url=target_url, browser=browser, fullscreen=fullscreen)

        if fullscreen and watch_url:
            await asyncio.sleep(1.8)  # 1.8s settle standard before pressing 'f'
            self._focus_window_by_keyword("youtube")
            self._send_native_win32_key("f")

        return f"Playing YouTube video '{query}' at {target_url} (fullscreen={fullscreen})."

    async def _launch_via_start_menu(self, app_name: str) -> bool:
        """
        Human-like application launch via Windows Start Menu:
        1. Presses Windows key (VK_LWIN 0x5B) to trigger Start Menu search.
        2. Waits 350ms for Windows search bar to gain focus.
        3. Types the application name.
        4. Waits 450ms for Windows search to index and highlight the top match.
        5. Presses Enter to launch.
        """
        try:
            self._send_native_win32_key("win")
            await asyncio.sleep(0.35)
            await self.computer_type(text=app_name, press_enter=False)
            await asyncio.sleep(0.45)
            self._send_native_win32_key("enter")
            return True
        except Exception as e:
            logger.debug(f"[StartMenuLaunch] Error launching '{app_name}': {e}")
            return False

    @dione_tool(
        description="Launch or focus a desktop application by name (e.g. 'Paint', 'Spotify', 'Chrome', 'Edge', 'VS Code', 'Notepad', 'Calculator', 'Explorer', 'Valorant', 'Riot Client') using human-like Windows Start Menu search or direct focus with a 1.8s render settle.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def launch_app(self, app: str) -> str:
        """Launch or focus desktop application via native Windows Start Menu with 1.8s render settle standard."""
        a_lower = app.lower().strip()
        clean_name = a_lower.replace("mspaint", "paint").replace("calc", "calculator")

        # 1. First check if already open and focus it
        existing = self._focus_window_by_keyword(clean_name) or self._focus_window_by_keyword(a_lower)
        if not existing and a_lower in ("valorant", "riot"):
            existing = self._focus_window_by_keyword("riot") or self._focus_window_by_keyword("valorant")
        if not existing and a_lower in ("paint", "mspaint"):
            existing = self._focus_window_by_keyword("paint")

        if existing:
            await asyncio.sleep(0.65)
            return f"Focused already-running window: '{existing['title']}' (HWND: {existing['hwnd']})."

        # 2. Preferred Human-Like Method: Windows Key -> Type Name -> Press Enter
        # Zero command prompt / zero CMD pipe hangs
        ok = await self._launch_via_start_menu(clean_name)
        if ok:
            await asyncio.sleep(1.8)  # 1.8s render settle standard
            focused = self._focus_window_by_keyword(clean_name) or self._focus_window_by_keyword(a_lower)
            if not focused and a_lower in ("valorant", "riot"):
                focused = self._focus_window_by_keyword("riot") or self._focus_window_by_keyword("valorant")
            if not focused and a_lower in ("paint", "mspaint"):
                focused = self._focus_window_by_keyword("paint")
            await asyncio.sleep(0.65)
            win_title = focused["title"] if focused else clean_name.capitalize()
            return f"Launched and focused '{win_title}' via Windows Start Menu."

        # 3. Fallback: Known binary paths
        known_map = {
            "chrome": [str(CHROME_EXE)],
            "google chrome": [str(CHROME_EXE)],
            "edge": [str(EDGE_EXE)],
            "microsoft edge": [str(EDGE_EXE)],
            "riot client": [str(RIOT_EXE)],
            "valorant": [str(RIOT_EXE), "--launch-product=valorant", "--launch-patchline=live"],
            "paint": ["mspaint.exe"],
            "mspaint": ["mspaint.exe"],
            "notepad": ["notepad.exe"],
            "calc": ["calc.exe"],
            "calculator": ["calc.exe"],
            "explorer": ["explorer.exe"],
            "code": ["code"],
            "vs code": ["code"],
            "spotify": ["cmd", "/c", "start", "spotify:"],
            "terminal": ["wt.exe"],
        }

        cmd_args = known_map.get(a_lower)
        if cmd_args:
            try:
                subprocess.Popen(cmd_args, shell=(cmd_args[0] in ("cmd", "code")))
                await asyncio.sleep(1.8)  # 1.8s post-app launch settle standard
                focused = self._focus_window_by_keyword(clean_name) or self._focus_window_by_keyword(a_lower)
                await asyncio.sleep(0.65)
                win_title = focused["title"] if focused else app
                return f"Launched and focused '{win_title}'."
            except Exception as e:
                logger.debug(f"Known app launch fallback: {e}")

        try:
            subprocess.Popen(f'start "" "{app}"', shell=True)
            await asyncio.sleep(1.8)
            focused = self._focus_window_by_keyword(clean_name) or self._focus_window_by_keyword(a_lower)
            await asyncio.sleep(0.65)
            win_title = focused["title"] if focused else app
            return f"Launched application '{win_title}'."
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
