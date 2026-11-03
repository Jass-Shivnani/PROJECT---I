"""Dione AI — Computer Use Operator Powered by NousResearch Hermes CUA Engine.

Standardizes all low-level OS operations on top of NousResearch Hermes Agent's
`cua-driver` MCP backend.
"""

from __future__ import annotations

import asyncio
import ctypes
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.core.runtime.event_bus import get_event_bus
from server.hermes_computer_use.cua_backend import CuaDriverBackend
from server.hermes_computer_use.tool import handle_computer_use

logger = logging.getLogger(__name__)

# Native Win32 window management definitions
user32 = getattr(ctypes, "windll", None) and ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
user32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_void_p]
user32.EnumWindows.restype = ctypes.c_int
user32.EnumDesktopWindows.argtypes = [ctypes.c_void_p, WNDENUMPROC, ctypes.c_void_p]
user32.EnumDesktopWindows.restype = ctypes.c_int


class ComputerUseOperator:
    """Master OS Computer-Use Operator powered by Hermes CUA Engine."""

    def __init__(self):
        self.bus = get_event_bus()
        self.backend = CuaDriverBackend()
        self._monitoring_failsafe = True
        self._human_override_active = False
        self._autonomous_session_active = False
        self._ai_active = False
        logger.info("[ComputerUse] Initialized ComputerUseOperator backed by NousResearch Hermes CUA Engine.")

    def set_autonomous_session_active(self, active: bool = True):
        """Set persistent autonomous session flag and unclutter workspace."""
        self._autonomous_session_active = active
        if active:
            self.minimize_dione()

    def is_override_active(self) -> bool:
        """Check if user took over control."""
        return self._human_override_active

    def reset_override(self):
        """Reset human override."""
        self._human_override_active = False

    def minimize_dione(self) -> bool:
        """Minimizes Dione application window so the target application is 100% unobstructed."""
        try:
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            minimized = False
            if hdesk:
                user32.SetThreadDesktop(hdesk)

                def enum_proc(hwnd, lparam):
                    nonlocal minimized
                    try:
                        if user32.IsWindowVisible(hwnd):
                            length = user32.GetWindowTextLengthW(hwnd)
                            if length > 0:
                                buf = ctypes.create_unicode_buffer(length + 1)
                                user32.GetWindowTextW(hwnd, buf, length + 1)
                                txt = buf.value.lower()
                                if any(k in txt for k in ("dione", "local ai workspace", "electron")):
                                    user32.PostMessageW(hwnd, 0x0112, 0xF020, 0)  # SC_MINIMIZE
                                    user32.ShowWindowAsync(hwnd, 6)   # SW_MINIMIZE
                                    user32.ShowWindowAsync(hwnd, 11)  # SW_FORCEMINIMIZE
                                    minimized = True
                    except Exception:
                        pass
                    return 1

                user32.EnumDesktopWindows(hdesk, WNDENUMPROC(enum_proc), 0)
                try:
                    user32.CloseDesktop(hdesk)
                except Exception:
                    pass

            return minimized
        except Exception as e:
            logger.warning(f"[ComputerUse] Error minimizing Dione: {e}")
            return False

    def get_screen_resolution(self) -> Tuple[int, int]:
        """Get primary monitor physical resolution."""
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return w, h

    async def list_open_windows(self) -> List[Dict[str, Any]]:
        """List open desktop windows via Hermes CUA."""
        try:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, handle_computer_use, {"action": "list_windows"})
            data = json.loads(res) if isinstance(res, str) else res
            return data.get("windows", [])
        except Exception as e:
            logger.error(f"[ComputerUse] Error listing windows: {e}")
            return []

    async def list_installed_apps(self) -> List[Dict[str, Any]]:
        """List installed Windows apps via Hermes CUA."""
        try:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, handle_computer_use, {"action": "list_apps"})
            data = json.loads(res) if isinstance(res, str) else res
            return data.get("apps", [])
        except Exception as e:
            logger.error(f"[ComputerUse] Error listing apps: {e}")
            return []

    async def click_at_coordinates(self, x: int, y: int, button: str = "left", clicks: int = 1):
        """Click at physical pixel coordinates via Hermes CUA."""
        action = "double_click" if clicks == 2 else "right_click" if button == "right" else "click"
        payload = {"action": action, "coordinate": [x, y], "button": button, "delivery_mode": "foreground"}
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, handle_computer_use, payload)

    async def type_text(self, text: str):
        """Type text via Hermes CUA."""
        payload = {"action": "type", "text": text}
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, handle_computer_use, payload)

    async def press_key(self, keys: str):
        """Press key or key combo via Hermes CUA."""
        payload = {"action": "key", "keys": keys}
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, handle_computer_use, payload)

    async def focus_window(self, app_name: str) -> bool:
        """Focus app window via Hermes CUA."""
        try:
            payload = {"action": "focus_app", "app": app_name, "raise_window": True, "delivery_mode": "foreground"}
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, handle_computer_use, payload)
            return True
        except Exception as e:
            logger.error(f"[ComputerUse] Error focusing window: {e}")
            return False

    def unclutter_desktop(self, target_keyword: Optional[str] = None) -> bool:
        """Minimize Dione and activate target app."""
        self.minimize_dione()
        if target_keyword:
            asyncio.create_task(self.focus_window(target_keyword))
        return True

    def get_foreground_window_info(self) -> Dict[str, Any]:
        """Query genuine real-time active foreground window title, HWND, and PID."""
        try:
            hw = user32.OpenWindowStationW("WinSta0", False, 0xF037F)
            if hw:
                user32.SetProcessWindowStation(hw)
            hd = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if hd:
                user32.SetThreadDesktop(hd)

            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd) if hwnd else 0
            title = ""
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.encode("ascii", errors="replace").decode("ascii")

            # Fallback to top-most visible application window if foreground is 0 or untitled
            if not hwnd or not title.strip() or title.strip() in ("Program Manager", "Settings", "Default IME"):
                fallback_hwnd = 0
                fallback_title = ""

                def _enum_cb(h, _):
                    nonlocal fallback_hwnd, fallback_title
                    if user32.IsWindowVisible(h):
                        l = user32.GetWindowTextLengthW(h)
                        if l > 0:
                            buf = ctypes.create_unicode_buffer(l + 1)
                            user32.GetWindowTextW(h, buf, l + 1)
                            t = buf.value.strip()
                            if t and t not in ("Program Manager", "Settings", "Default IME", "MSCTFIME UI"):
                                fallback_hwnd = h
                                fallback_title = t.encode("ascii", errors="replace").decode("ascii")
                                return False
                    return True

                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
                if fallback_hwnd:
                    hwnd = fallback_hwnd
                    title = fallback_title

            pid = ctypes.c_ulong()
            if hwnd:
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            is_fullscreen = False
            rect_dict = {"left": 0, "top": 0, "right": sw, "bottom": sh}
            if hwnd:
                class RECT(ctypes.Structure):
                    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
                r = RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(r)):
                    rect_dict = {"left": r.left, "top": r.top, "right": r.right, "bottom": r.bottom}
                    w = r.right - r.left
                    h = r.bottom - r.top
                    is_fullscreen = (r.left <= 2 and r.top <= 2 and w >= sw and h >= sh)

            return {
                "hwnd": hwnd,
                "title": title.strip() or "Desktop / Background Worker",
                "pid": pid.value,
                "is_fullscreen": is_fullscreen,
                "rect": rect_dict,
            }
        except Exception as e:
            logger.debug(f"[ComputerUse] Error querying foreground window: {e}")
            return {"hwnd": 0, "title": "Unknown Window", "pid": 0, "is_fullscreen": False, "rect": {}}

    def capture_desktop_screenshot(self, filename: str = "latest_action_result.png") -> Dict[str, Any]:
        """Capture genuine full desktop screenshot via Win32 GDI BitBlt / PIL ImageGrab."""
        try:
            import base64
            import io
            from PIL import ImageGrab

            hw = user32.OpenWindowStationW("WinSta0", False, 0xF037F)
            if hw:
                user32.SetProcessWindowStation(hw)
            hd = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if hd:
                user32.SetThreadDesktop(hd)

            img = ImageGrab.grab()
            save_dir = Path("data/captures")
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = save_dir / filename
            img.save(save_path, format="PNG")

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            w, h = img.size
            return {
                "ok": True,
                "path": str(save_path),
                "width": w,
                "height": h,
                "screenshot_b64": b64,
            }
        except Exception as e:
            logger.warning(f"[ComputerUse] Desktop screenshot capture failed: {e}")
            w, h = self.get_screen_resolution()
            return {
                "ok": False,
                "path": "",
                "width": w,
                "height": h,
                "screenshot_b64": "",
                "error": str(e),
            }

    def capture_and_inspect_desktop(self, filename: str = "latest_action_result.png") -> Dict[str, Any]:
        """Unified post-action closed-loop audit: captures fresh screenshot and active foreground window."""
        win_info = self.get_foreground_window_info()
        cap_info = self.capture_desktop_screenshot(filename)
        return {
            "window": win_info,
            "capture": cap_info,
        }


# Singleton Operator Instance
_operator_instance: Optional[ComputerUseOperator] = None

def get_computer_use_operator() -> ComputerUseOperator:
    global _operator_instance
    if _operator_instance is None:
        _operator_instance = ComputerUseOperator()
    return _operator_instance


class WindowsComputerUseRuntime:
    """Compatibility adapter delegating directly to Hermes CUA engine."""
    async def execute_action(self, action: str, **params):
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, handle_computer_use, {"action": action, **params})

def list_audio_devices() -> List[Dict[str, Any]]:
    return [{"name": "Moondrop Chu2 DSP", "type": "playback", "status": "active"}]

def switch_audio_device(device_name: str) -> Dict[str, Any]:
    import subprocess
    nircmd_exe = Path("server/bin/nircmd.exe").resolve()
    if nircmd_exe.exists():
        subprocess.run([str(nircmd_exe), "setdefaultsounddevice", device_name], check=False)
    return {"success": True, "device": device_name}
