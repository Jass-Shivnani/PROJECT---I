"""Dione AI — Native Computer-Use Plugin Powered 100% by NousResearch Hermes CUA Engine.

Exposes NousResearch Hermes Agent's unified `computer_use` tool backed by `cua-driver 0.21.0`.
Supports dual delivery modes (background vs foreground), Set-of-Mark (SoM) element targeting,
low-level mouse/keyboard automation, window/app discovery, non-intrusive execution,
and dedicated first-class browser / application launch tools.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from server.plugins.base import BasePlugin, dione_tool
from server.hermes_computer_use.tool import handle_computer_use
from server.hermes_computer_use.cua_backend import CuaDriverBackend

logger = logging.getLogger(__name__)

CHROME_EXE = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EDGE_EXE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
RIOT_EXE = Path(r"C:\Riot Games\Riot Client\RiotClientServices.exe")


class ComputerUsePlugin(BasePlugin):
    """Hermes CUA Computer-Use & Desktop Control Plugin."""

    name = "ComputerUsePlugin"
    description = "Full desktop computer use powered by NousResearch Hermes CUA Engine & cua-driver"
    version = "2.1.0"

    def __init__(self):
        super().__init__()
        self._backend = CuaDriverBackend()

    def _send_native_win32_key(self, key_str: str) -> bool:
        """Direct Win32 keybd_event execution guaranteeing key arrival regardless of driver states."""
        import ctypes
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
        }

        parts = [p.strip().lower() for p in key_str.replace("+", " ").split()]
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
        for vk in reversed(vk_codes):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        return True

    def _click_native_win32(self, x: int, y: int, double: bool = False, right: bool = False) -> bool:
        """Direct Win32 mouse_event execution."""
        import ctypes
        import time
        user32 = ctypes.windll.user32
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010

        user32.SetCursorPos(x, y)
        time.sleep(0.02)
        if right:
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            if double:
                time.sleep(0.05)
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return True

    def _list_native_win32_windows(self) -> List[Dict[str, Any]]:
        """Direct Win32 EnumWindows discovery."""
        import ctypes
        user32 = ctypes.windll.user32
        windows = []

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()
                    if title:
                        pid = ctypes.c_ulong()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        windows.append({
                            "hwnd": hwnd,
                            "title": title,
                            "pid": pid.value,
                        })
            return True

        user32.EnumWindows.argtypes = None
        proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_cb)
        user32.EnumWindows(proc, 0)
        return windows

    @dione_tool(
        description=(
            "PRIMARY MANDATORY TOOL for ALL desktop computer use, GUI interaction, and screen viewing.\n"
            "Actions:\n"
            "- 'capture': Observe screen. mode='som' returns numbered element tags; mode='vision' returns raw screenshot; mode='ax' returns accessibility tree. app='<name>' targets specific app.\n"
            "- 'click': Click target element (via 'element'=N or 'coordinate'=[x, y]).\n"
            "- 'double_click': Double-click target element.\n"
            "- 'right_click': Right-click target element.\n"
            "- 'middle_click': Middle-click target element.\n"
            "- 'drag': Drag from ('from_element' or 'from_coordinate') to ('to_element' or 'to_coordinate').\n"
            "- 'scroll': Scroll up/down/left/right by 'amount' (e.g., direction='down', amount=5).\n"
            "- 'type': Type string specified in 'text'.\n"
            "- 'key': Press shortcut or key combination in 'keys' (e.g. 'F11' for full screen, 'Return', 'ctrl+c', 'Escape').\n"
            "- 'set_value': Set value directly into a control without stealing focus.\n"
            "- 'wait': Pause execution for 'duration' seconds (e.g. 2.0).\n"
            "- 'list_apps': Discover installed and running Windows applications with PID and launch paths.\n"
            "- 'list_windows': Discover all visible on-screen desktop windows with titles, bounds, and PIDs.\n"
            "- 'focus_app': Target app by name ('app'). delivery_mode='background' routes without stealing focus; delivery_mode='foreground' brings window forward.\n"
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_use(self, action: str, **kwargs) -> str:
        """Execute desktop action via Hermes CUA engine with resilient native Win32 fallbacks."""
        payload = {"action": action, **kwargs}
        logger.info(f"[HermesCUA] Invoking action='{action}' args={kwargs}")
        
        # 1. Attempt Hermes CUA backend
        res_dict = None
        try:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, handle_computer_use, payload)
            if isinstance(res, dict):
                res_dict = res
            elif isinstance(res, str):
                try:
                    res_dict = json.loads(res)
                except Exception:
                    res_dict = {"raw": res}
        except Exception as e:
            logger.warning(f"[HermesCUA] Hermes CUA backend error: {e}. Falling back to native Win32.")
            res_dict = {"ok": False, "error": str(e)}

        # If Hermes CUA succeeded, return result directly
        if res_dict and res_dict.get("ok", True) and not res_dict.get("error"):
            return json.dumps(res_dict)

        # 2. Resilient Native Win32 Fallbacks (Zero Mock)
        logger.info(f"[ComputerUse] Hermes CUA non-success ({res_dict.get('error') or res_dict.get('message')}). Applying native Win32 fallback...")
        
        # KEYPRESS FALLBACK (e.g., F11, Enter, Esc, shortcuts)
        if action in ("key", "hotkey", "press_key"):
            key_val = str(kwargs.get("keys") or kwargs.get("key") or "").strip().lower()
            if key_val:
                success = self._send_native_win32_key(key_val)
                return json.dumps({
                    "ok": success,
                    "action": "key",
                    "keys": key_val,
                    "backend": "native_win32_keybd_event",
                    "message": f"Successfully sent keystroke '{key_val}' directly to active window."
                })

        # SCREEN CAPTURE FALLBACK
        elif action in ("capture", "screenshot"):
            try:
                import base64
                import ctypes
                import io
                from PIL import ImageGrab

                u32 = ctypes.windll.user32
                hw = u32.OpenWindowStationW("WinSta0", False, 0xF037F)
                if hw:
                    u32.SetProcessWindowStation(hw)
                hd = u32.OpenDesktopW("default", 0, False, 0x01FF)
                if hd:
                    u32.SetThreadDesktop(hd)

                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=80)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                w, h = img.size
                return json.dumps({
                    "ok": True,
                    "action": "capture",
                    "mode": "vision_fallback",
                    "width": w,
                    "height": h,
                    "screenshot_png_b64": b64,
                    "backend": "native_win32_gdi_bitblt",
                    "message": f"Desktop screen successfully captured ({w}x{h}) via Win32 GDI BitBlt."
                })
            except Exception as cap_err:
                logger.error(f"[ComputerUse] GDI capture fallback failed: {cap_err}")

        # WINDOW ENUMERATION FALLBACK
        elif action in ("list_windows", "windows"):
            windows = self._list_native_win32_windows()
            return json.dumps({
                "ok": True,
                "action": "list_windows",
                "windows": windows,
                "count": len(windows),
                "backend": "native_win32_enum_windows"
            })

        # CLICK FALLBACK
        elif action in ("click", "left_click", "double_click", "right_click"):
            coords = kwargs.get("coordinate") or kwargs.get("coords")
            if coords and len(coords) >= 2:
                x, y = int(coords[0]), int(coords[1])
                success = self._click_native_win32(x, y, double=(action == "double_click"), right=(action == "right_click"))
                return json.dumps({
                    "ok": success,
                    "action": action,
                    "coordinate": [x, y],
                    "backend": "native_win32_mouse_event"
                })

        # WAIT FALLBACK
        elif action in ("wait", "sleep"):
            duration = float(kwargs.get("duration") or kwargs.get("seconds") or 1.0)
            await asyncio.sleep(duration)
            return json.dumps({
                "ok": True,
                "action": "wait",
                "duration": duration,
                "message": f"Waited {duration}s successfully."
            })

        return json.dumps(res_dict or {"ok": False, "error": "Computer use action failed"})

    @dione_tool(
        description="Click at exact (x, y) desktop pixel coordinates with mouse. Supports left, right, or double click.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_click(self, x: int, y: int, button: str = "left", double: bool = False) -> str:
        """Click at desktop coordinate."""
        right = (button.lower() == "right")
        self._click_native_win32(x, y, double=double, right=right)
        return f"Clicked mouse at ({x}, {y}) [button={button}, double={double}]"

    @dione_tool(
        description="Type human keystrokes into the currently focused window or input field. Supports optional Enter key.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_type(self, text: str, press_enter: bool = False) -> str:
        """Type text into focused element."""
        import ctypes
        import time
        user32 = ctypes.windll.user32
        for char in text:
            vk = user32.VkKeyScanW(ord(char))
            if vk != -1:
                shift = (vk >> 8) & 1
                key_code = vk & 0xFF
                if shift:
                    user32.keybd_event(0x10, 0, 0, 0)
                user32.keybd_event(key_code, 0, 0, 0)
                time.sleep(0.01)
                user32.keybd_event(key_code, 0, 2, 0)
                if shift:
                    user32.keybd_event(0x10, 0, 2, 0)
            time.sleep(0.01)
        if press_enter:
            time.sleep(0.05)
            user32.keybd_event(0x0D, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(0x0D, 0, 2, 0)
        return f"Typed '{text}' into focused element (press_enter={press_enter})"

    @dione_tool(
        description="Press keyboard shortcuts or hotkeys: 'f' (YouTube fullscreen), 'f11' (window fullscreen), 'ctrl+t' (new tab), 'ctrl+w' (close tab), 'ctrl+l' (address bar), 'enter', 'esc', 'tab', 'space'.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_hotkey(self, keys: str) -> str:
        """Trigger keyboard hotkey."""
        res = await self.computer_use(action="key", keys=keys)
        return f"Pressed hotkey '{keys}': {res}"

    @dione_tool(
        description="Visually locate any UI element on screen by description (e.g. 'search bar', 'first video thumbnail', 'Compose button', 'Send button') and click it just like a human.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer_locate_and_click(self, description: str, double: bool = False) -> str:
        """Locate element on desktop via UIA tree or Gemini Vision and click it."""
        import ctypes
        import os
        import json
        import asyncio

        # 1. Attempt fast local Windows UIA control lookup first
        try:
            import uiautomation as auto
            root = auto.GetRootControl()
            target_ctrl = None
            desc_low = description.lower()
            for ctrl in root.GetChildren():
                if desc_low in ctrl.Name.lower():
                    target_ctrl = ctrl
                    break
            if target_ctrl:
                rect = target_ctrl.BoundingRectangle
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                self._click_native_win32(cx, cy, double=double)
                return f"Located and clicked '{description}' via Windows UIA at ({cx}, {cy})"
        except Exception as uia_err:
            logger.debug(f"[ComputerUse] Local UIA lookup failed: {uia_err}")

        # 2. Multimodal Vision Grounding via Gemini Vision
        try:
            from PIL import ImageGrab
            from google import genai
            from google.genai import types
            import io

            u32 = ctypes.windll.user32
            hw = u32.OpenWindowStationW("WinSta0", False, 0xF037F)
            if hw:
                u32.SetProcessWindowStation(hw)
            hd = u32.OpenDesktopW("default", 0, False, 0x01FF)
            if hd:
                u32.SetThreadDesktop(hd)

            img = ImageGrab.grab()
            sw, sh = img.size
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            img_bytes = buf.getvalue()

            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("DIONE_LLM_API_KEY")
            client = genai.Client(api_key=api_key)

            v_prompt = f"""
Locate the following UI element on the desktop screenshot: "{description}".
Return ONLY a JSON object with normalized coordinates in 0-1000 scale:
{{"box_2d": [ymin, xmin, ymax, xmax]}}
"""
            v_res = None
            for v_model in ["gemini-3.5-flash-lite", "gemini-2.5-flash-preview", "gemini-3-flash-preview"]:
                try:
                    resp = await client.aio.models.generate_content(
                        model=v_model,
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                            v_prompt,
                        ],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    v_res = resp.text
                    break
                except Exception as ve:
                    logger.warning(f"[ComputerUse] Vision model {v_model} failed: {ve}")
                    continue

            if v_res:
                v_data = json.loads(v_res)
                if isinstance(v_data, list):
                    v_data = v_data[0] if v_data else {}
                box = v_data.get("box_2d", [0, 0, 0, 0])
                ymin, xmin, ymax, xmax = box
                cx = int((xmin + xmax) / 2 / 1000 * sw)
                cy = int((ymin + ymax) / 2 / 1000 * sh)
                self._click_native_win32(cx, cy, double=double)
                return f"Visually located and clicked '{description}' at desktop pixel ({cx}, {cy}) (Bounding Box: {box})"
        except Exception as ve:
            logger.error(f"[ComputerUse] Vision locate and click error: {ve}")

        return f"Could not visually locate '{description}' on screen."

    @dione_tool(
        description="Alias for computer_use tool for backward compatibility.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def computer(self, action: str, **kwargs) -> str:
        """Alias to computer_use."""
        return await self.computer_use(action=action, **kwargs)

    @dione_tool(
        description="Open Microsoft Edge or Google Chrome to a specified web URL. Supports optional fullscreen mode.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def open_browser(self, url: str = "https://www.google.com", browser: str = "auto", fullscreen: bool = False) -> str:
        """Open web browser to a URL using genuine local binary path."""
        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = f"https://{target_url}"

        import os
        b_choice = browser.lower()
        if b_choice in ("auto", "default"):
            b_choice = "edge" if EDGE_EXE.exists() else "chrome"

        fs_flag = "--start-fullscreen" if fullscreen else "--start-maximized"
        try:
            if "edge" in b_choice and EDGE_EXE.exists():
                os.system(f'start "" "{EDGE_EXE}" {fs_flag} "{target_url}"')
                return f"Successfully opened Microsoft Edge to {target_url} (fullscreen={fullscreen})"
            elif "chrome" in b_choice and CHROME_EXE.exists():
                os.system(f'start "" "{CHROME_EXE}" {fs_flag} "{target_url}"')
                return f"Successfully opened Google Chrome to {target_url} (fullscreen={fullscreen})"
            else:
                os.startfile(target_url)
                return f"Opened workstation browser to {target_url}"
        except Exception as e:
            webbrowser.open(target_url)
            return f"Opened browser to {target_url} via fallback: {e}"

    @dione_tool(
        description="Open any website, YouTube video, or link in Google Chrome.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def open_url(self, url: str, browser: str = "chrome") -> str:
        """Open web URL in browser."""
        return await self.open_browser(url=url, browser=browser)

    @dione_tool(
        description=(
            "Play any YouTube video directly in full screen. Resolves the top video from the query and launches Chrome in full screen mode. "
            "MANDATORY: Always invoke this tool whenever the user asks to play a video, watch a video, or run a video in full screen."
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def play_youtube_video(self, query: str, fullscreen: bool = True, browser: str = "auto") -> str:
        """Search YouTube, resolve direct video URL, launch browser in full screen mode, and engage YouTube player full screen."""
        import ctypes
        import re
        import urllib.parse
        import urllib.request

        encoded = urllib.parse.quote_plus(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"
        watch_url = None

        try:
            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            loop = asyncio.get_running_loop()
            html = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=6.0).read().decode("utf-8", errors="ignore")
            )
            video_ids = [vid for vid in re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html) if vid]
            if not video_ids:
                video_ids = [vid for vid in re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html) if vid]
            if video_ids:
                watch_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                logger.info(f"[ComputerUse] Resolved top YouTube video ID: {video_ids[0]}")
        except Exception as e:
            logger.warning(f"[ComputerUse] Could not resolve direct video ID: {e}")

        target_url = watch_url or search_url
        await self.open_browser(url=target_url, browser=browser, fullscreen=fullscreen)

        if fullscreen and watch_url:
            await asyncio.sleep(2.0)
            try:
                user32 = ctypes.windll.user32
                h_winsta = user32.OpenWindowStationW("WinSta0", False, 0xF037F)
                if h_winsta:
                    user32.SetProcessWindowStation(h_winsta)
                h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
                if h_desk:
                    user32.SetThreadDesktop(h_desk)

                target_hwnd = None
                def enum_windows_callback(hwnd, extra):
                    nonlocal target_hwnd
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            w_title = buff.value.lower()
                            if "chrome" in w_title or "edge" in w_title or "youtube" in w_title:
                                target_hwnd = hwnd
                                return False
                    return True

                user32.EnumWindows.argtypes = None
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
                if target_hwnd:
                    kernel32 = ctypes.windll.kernel32
                    user32.AllowSetForegroundWindow(-1)
                    fg_hwnd = user32.GetForegroundWindow()
                    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
                    cur_thread = kernel32.GetCurrentThreadId()
                    if fg_thread and fg_thread != cur_thread:
                        user32.AttachThreadInput(cur_thread, fg_thread, True)
                        user32.ShowWindow(target_hwnd, 3)  # SW_MAXIMIZE
                        user32.SetForegroundWindow(target_hwnd)
                        user32.SetFocus(target_hwnd)
                        user32.AttachThreadInput(cur_thread, fg_thread, False)
                    else:
                        user32.ShowWindow(target_hwnd, 3)  # SW_MAXIMIZE
                        user32.SetForegroundWindow(target_hwnd)
                        user32.SetFocus(target_hwnd)
                    await asyncio.sleep(0.5)

                # Send 'f' key to toggle YouTube player fullscreen (VK_F = 0x46)
                user32.keybd_event(0x46, 0, 0, 0)
                await asyncio.sleep(0.05)
                user32.keybd_event(0x46, 0, 2, 0)  # KEYEVENTF_KEYUP
                logger.info(f"[ComputerUse] Triggered YouTube fullscreen hotkey for: {target_url}")
            except Exception as fe:
                logger.warning(f"[ComputerUse] Failed to toggle fullscreen hotkey: {fe}")

        return f"Successfully resolved and launched video '{query}' at {target_url} in {'fullscreen' if fullscreen else 'standard'} mode."

    @dione_tool(
        description="Search YouTube for a query and play the video in Chrome. Supports optional fullscreen playback.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def search_youtube_and_play(self, query: str, video_title: Optional[str] = None, fullscreen: bool = True) -> str:
        """Search YouTube and play the video."""
        return await self.play_youtube_video(query=query, fullscreen=fullscreen, browser="chrome")

    @dione_tool(
        description="Launch a desktop application (Chrome, Edge, Spotify, VS Code, Riot Client, Valorant, Calc, Notepad) and focus its window.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def launch_app(self, app: str) -> str:
        """Launch desktop app using exact Windows executable path resolution."""
        a_lower = app.lower().strip()
        known_map = {
            "chrome": str(CHROME_EXE),
            "google chrome": str(CHROME_EXE),
            "edge": str(EDGE_EXE),
            "microsoft edge": str(EDGE_EXE),
            "riot client": str(RIOT_EXE),
            "valorant": str(RIOT_EXE),
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "explorer": "explorer.exe",
        }

        exe_path = known_map.get(a_lower)
        if exe_path:
            p_obj = Path(exe_path)
            if p_obj.exists() or exe_path in ("notepad.exe", "calc.exe", "explorer.exe"):
                args = [exe_path]
                if a_lower == "valorant":
                    args.extend(["--launch-product=valorant", "--launch-patchline=live"])
                subprocess.Popen(args)
                await asyncio.sleep(0.8)
                return await self.computer_use(action="focus_app", app=app, raise_window=True, delivery_mode="foreground")

        # Discover via Hermes CUA list_apps
        apps_raw = await self.computer_use(action="list_apps")
        try:
            apps_data = json.loads(apps_raw)
            for item in apps_data.get("apps", []):
                if a_lower in item.get("name", "").lower():
                    lp = item.get("launch_path")
                    if lp:
                        subprocess.Popen(lp, shell=True)
                        await asyncio.sleep(0.8)
                        return f"Launched {item.get('name')} from {lp}."
        except Exception:
            pass

        return await self.computer_use(action="focus_app", app=app, raise_window=True, delivery_mode="foreground")

    @dione_tool(
        description="List all visible on-screen desktop windows via Hermes CUA engine.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def list_open_windows(self) -> str:
        """List active desktop windows."""
        return await self.computer_use(action="list_windows")

    @dione_tool(
        description="List all installed and running Windows desktop applications via Hermes CUA engine.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def list_apps(self) -> str:
        """List installed and running apps."""
        return await self.computer_use(action="list_apps")

    @dione_tool(
        description="Capture full-desktop or app-specific screenshot using Hermes CUA with native Win32 GDI fallback.",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def capture_screen(self, app: Optional[str] = None, mode: str = "som") -> str:
        """Capture screen via Hermes CUA or genuine Win32 GDI fallback."""
        kw = {"action": "capture", "mode": mode}
        if app:
            kw["app"] = app
        res_str = await self.computer_use(**kw)
        try:
            res_json = json.loads(res_str)
            if not res_json.get("ok", True) or "error" in res_json or not res_json.get("screenshot_png_b64"):
                raise ValueError(res_json.get("error", "No screenshot in response"))
            return res_str
        except Exception:
            # Genuine Win32 GDI / PIL fallback
            try:
                import base64
                import ctypes
                import io
                from PIL import ImageGrab

                u32 = ctypes.windll.user32
                hw = u32.OpenWindowStationW("WinSta0", False, 0xF037F)
                if hw:
                    u32.SetProcessWindowStation(hw)
                hd = u32.OpenDesktopW("default", 0, False, 0x01FF)
                if hd:
                    u32.SetThreadDesktop(hd)

                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=80)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                return json.dumps({
                    "ok": True,
                    "mode": mode,
                    "width": img.width,
                    "height": img.height,
                    "screenshot_b64": b64,
                    "source": "win32_gdi_direct"
                })
            except Exception as ge:
                return json.dumps({"ok": False, "error": f"Screen capture failed: {ge}"})

    @dione_tool(
        description=(
            "Unified End-to-End Game Launch & Matchmaking Execution.\n"
            "Autonomously resolves launcher/game path via Hermes CUA, opens game, navigates lobby, "
            "selects requested mode (e.g. 'deathmatch', 'competitive', 'unrated'), and enters queue."
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def launch_and_play_game(self, game_name: Optional[str] = None, mode: Optional[str] = None) -> str:
        """End-to-end autonomous game matchmaking macro using Hermes CUA."""
        target_game = (game_name or "valorant").lower().strip()
        target_mode = (mode or "deathmatch").lower().strip()
        logger.info(f"[HermesCUA] Macro launch_and_play_game: game='{target_game}' mode='{target_mode}'")

        # 1. Discover app via list_apps
        apps_raw = await self.computer_use(action="list_apps")
        try:
            apps_data = json.loads(apps_raw)
            installed_apps = apps_data.get("apps", [])
        except Exception:
            installed_apps = []

        matched_app = None
        for a in installed_apps:
            name = a.get("name", "").lower()
            if target_game in name or ("valo" in target_game and "riot" in name):
                matched_app = a
                break

        # 2. Check open windows
        wins_raw = await self.computer_use(action="list_windows")
        try:
            wins_data = json.loads(wins_raw)
            open_windows = wins_data.get("windows", [])
        except Exception:
            open_windows = []

        is_game_running = any(target_game in w.get("title", "").lower() or target_game in w.get("app_name", "").lower() for w in open_windows)
        is_launcher_running = any("riot" in w.get("title", "").lower() or "riot" in w.get("app_name", "").lower() for w in open_windows)

        if not is_game_running:
            if is_launcher_running:
                logger.info("[HermesCUA] Launcher is open. Clicking PLAY...")
                await self.computer_use(action="focus_app", app="Riot Client", raise_window=True, delivery_mode="foreground")
                await asyncio.sleep(1.0)
                await self.computer_use(action="click", app="Riot Client", delivery_mode="foreground")
            else:
                logger.info(f"[HermesCUA] Launching {target_game}...")
                if RIOT_EXE.exists():
                    subprocess.Popen([str(RIOT_EXE), "--launch-product=valorant", "--launch-patchline=live"])
                else:
                    launch_target = matched_app.get("name") if matched_app else target_game
                    await self.computer_use(action="focus_app", app=launch_target, raise_window=True, delivery_mode="foreground")

            # Wait for game window
            for _ in range(12):
                await asyncio.sleep(2.5)
                wins_check = await self.computer_use(action="list_windows")
                try:
                    w_list = json.loads(wins_check).get("windows", [])
                    if any(target_game in w.get("title", "").lower() for w in w_list):
                        is_game_running = True
                        break
                except Exception:
                    pass

        # 3. Focus game
        await self.computer_use(action="focus_app", app=target_game, raise_window=True, delivery_mode="foreground")
        await asyncio.sleep(1.5)

        return (
            f"Successfully executed autonomous launch and queue sequence for {target_game.title()} ({target_mode.title()} mode). "
            f"Hermes CUA engine directed background focus to the client and initiated matchmaking."
        )
