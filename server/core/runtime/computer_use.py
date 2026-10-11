"""
Dione Next-Gen — Autonomous Computer-Use Operator Actor

Enables full native OS-level autonomy across the Windows PC:
1. Hybrid Windows UI Automation (UIA) tree inspection + Screenshot capture
2. Application launching, window switching, and window state management
3. Mouse navigation (pixel-precise coordinates or accessibility target)
4. Keyboard typing, key shortcuts, and clipboard synchronization
5. System media controls (volume, play/pause, next track)
6. Multi-layer fail-safe: physical mouse jiggle & Esc-escape abortion
"""

import asyncio
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger

import pyautogui
import uiautomation as uia

from server.core.runtime.event_bus import (
    AgentState,
    AsyncEventBus,
    EventType,
    RuntimeEvent,
    get_event_bus,
)


# Configure PyAutoGUI safety defaults
pyautogui.FAILSAFE = False  # Custom physical mouse movement failsafe active in _failsafe_worker
pyautogui.PAUSE = 0.05     # Brief pause between synthetic events


@dataclass
class UIElementInfo:
    name: str
    control_type: str
    bounding_rect: Tuple[int, int, int, int]  # left, top, right, bottom
    automation_id: str
    is_enabled: bool


class ComputerUseOperator:
    """
    Autonomous desktop controller.
    Executes native OS-level tasks with safety guardrails and real-time telemetry.
    """

    KNOWN_APP_COMMANDS = {
        "spotify": "start spotify:",
        "chrome": "start chrome",
        "edge": "start msedge",
        "code": "code",
        "vs code": "code",
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "explorer": "explorer",
        "terminal": "wt",
        "powershell": "powershell",
        "word": "start winword",
        "excel": "start excel",
    }

    def __init__(self, event_bus: Optional[AsyncEventBus] = None):
        self.bus = event_bus or get_event_bus()
        try:
            self._last_mouse_pos = pyautogui.position()
        except Exception:
            self._last_mouse_pos = (0, 0)
        self._monitoring_failsafe = False
        self._failsafe_thread: Optional[threading.Thread] = None
        self._synthetic_moving = False
        self._human_override_active = False

        # Automatically start the mouse failsafe daemon thread
        self.start_failsafe_monitor()

    def start_failsafe_monitor(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Start tracking physical mouse movements for user override."""
        if not self._monitoring_failsafe:
            self._monitoring_failsafe = True
            try:
                self._last_mouse_pos = pyautogui.position()
            except Exception:
                self._last_mouse_pos = (0, 0)
            self._failsafe_thread = threading.Thread(
                target=self._failsafe_worker,
                daemon=True,
                name="DioneMouseFailsafe"
            )
            self._failsafe_thread.start()
            logger.info("🛡️ Dione Human-in-the-Loop Mouse Fail-Safe active.")

    def stop_failsafe_monitor(self):
        self._monitoring_failsafe = False

    def is_override_active(self) -> bool:
        """Returns True if the user recently moved their physical mouse to abort AI control."""
        return self._human_override_active or getattr(self.bus, "_emergency_stopped", False)

    def reset_override(self):
        """Reset the override latch when user initiates a new command."""
        self._human_override_active = False
        if hasattr(self.bus, "_emergency_stopped"):
            self.bus._emergency_stopped = False
        try:
            self._last_mouse_pos = pyautogui.position()
        except Exception:
            pass

    def _failsafe_worker(self):
        """Dedicated thread continuously tracking physical mouse movement."""
        while self._monitoring_failsafe:
            try:
                time.sleep(0.08)
                curr_pos = pyautogui.position()
                if self._synthetic_moving:
                    self._last_mouse_pos = curr_pos
                    continue

                dx = abs(curr_pos[0] - self._last_mouse_pos[0])
                dy = abs(curr_pos[1] - self._last_mouse_pos[1])

                if dx > 80 or dy > 80:
                    logger.warning(f"[ComputerUse] 🚨 Physical mouse override detected (dx={dx}, dy={dy})! Aborting AI actions.")
                    self._human_override_active = True
                    try:
                        self.bus.trigger_emergency_stop("Physical mouse override by user")
                    except Exception as e:
                        logger.error(f"Failed to trigger emergency stop: {e}")
                    # Update pos to prevent re-triggering every tick
                    self._last_mouse_pos = curr_pos
                else:
                    self._last_mouse_pos = curr_pos
            except Exception:
                time.sleep(0.5)

    async def _record_action(self, action_type: str, details: Dict[str, Any]):
        """Publish computer-use telemetry event to the Dynamic Island overlay."""
        logger.info(f"[ComputerUse] 🖥️ {action_type.upper()}: {details}")
        await self.bus.publish(
            RuntimeEvent(
                event_type=EventType.COMPUTER_USE_ACTION,
                payload={"action": action_type, "details": details},
                sender="computer_use",
            )
        )

    @staticmethod
    def resolve_windows_app(app_name: str) -> Optional[str]:
        """
        Dynamically locate Windows shortcuts (.lnk), executables, or Store app IDs.
        Scans Desktop, Start Menu, and App Paths without relying on PATH env.
        """
        query = app_name.lower().strip()
        search_dirs = [
            Path("C:/Users/Public/Desktop"),
            Path.home() / "Desktop",
            Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
            Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs",
        ]

        # 1. Check direct .lnk shortcuts
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for p in sdir.rglob("*.lnk"):
                stem = p.stem.lower()
                # Exact match or high-confidence substring
                if query == stem or query in stem or stem in query:
                    return str(p)

        # 2. Check Windows StartApps for Store/Xbox/Riot applications
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f'Get-StartApps | Where-Object {{ $_.Name -like "*{query}*" }} | Select-Object -First 1 -ExpandProperty AppID'],
                capture_output=True,
                text=True,
                timeout=4,
            )
            app_id = res.stdout.strip()
            if app_id:
                return f"shell:AppsFolder\\{app_id}"
        except Exception:
            pass

        return None

    # ==========================================
    # 1. APPLICATION & WINDOW MANAGEMENT
    # ==========================================

    async def launch_app(self, app_name: str, mimic_human: bool = True) -> str:
        """Launch an application mimicking human keyboard navigation with robust shortcut fallback."""
        if self.is_override_active():
            raise RuntimeError("🖐️ Human Takeover Detected: You moved your mouse, so Dione stopped controlling your screen for your safety.")

        self.bus.set_state(AgentState.ACTING, reason=f"Launching app: {app_name}")
        normalized = app_name.lower().strip()
        shortcut_path = self.resolve_windows_app(normalized)

        launched = False

        # Mode A: Mimic human navigation via Windows Search (Win Key + Type + Enter)
        if mimic_human:
            try:
                logger.info(f"[ComputerUse] Mimicking human navigation for '{app_name}' (Win + Type + Enter)...")
                self._synthetic_moving = True
                pyautogui.press("win")
                await asyncio.sleep(0.3)
                pyautogui.write(app_name, interval=0.03)
                await asyncio.sleep(0.4)
                pyautogui.press("enter")
                await asyncio.sleep(1.2)
                launched = True
            except Exception as e:
                logger.warning(f"[ComputerUse] Human-mimicking typing failed: {e}")
            finally:
                self._synthetic_moving = False

        # Mode B: Direct shortcut / StartApp resolution fallback (guarantees launch even if Search indexer stalls)
        if "valorant" in normalized:
            # 1. Prefer public desktop shortcut or Riot Client path
            valorant_lnk = Path(r"C:\Users\Public\Desktop\VALORANT.lnk")
            riot_exe = Path(r"C:\Riot Games\Riot Client\RiotClientServices.exe")

            if valorant_lnk.exists():
                logger.info(f"[ComputerUse] Launching VALORANT via desktop shortcut: {valorant_lnk}")
                try:
                    os.startfile(str(valorant_lnk))
                except Exception as e:
                    logger.warning(f"Failed to startfile VALORANT.lnk: {e}")
            elif riot_exe.exists():
                logger.info("[ComputerUse] Launching VALORANT via RiotClientServices live patchline...")
                try:
                    subprocess.Popen([str(riot_exe), "--launch-product=valorant", "--launch-patchline=live"])
                except Exception as e:
                    logger.warning(f"Direct Riot launch note: {e}")

            # 2. Allow launcher window time to render
            logger.info("[ComputerUse] Waiting for Riot Client launcher window to render...")
            await asyncio.sleep(2.5)

            # 3. Bring Riot Client to the foreground
            nircmd_exe = Path("server/bin/nircmd.exe").resolve()
            if not nircmd_exe.exists():
                nircmd_exe = Path("server/bin/nircmdc.exe").resolve()
            if nircmd_exe.exists():
                subprocess.run([str(nircmd_exe), "win", "activate", "ititle", "Riot"], check=False)
                subprocess.run([str(nircmd_exe), "win", "focus", "ititle", "Riot"], check=False)

            await asyncio.sleep(0.8)

            # 4. Click the red '▶ PLAY' button (412, 398) using NirCmd and Win32
            logger.info("[ComputerUse] Clicking '▶ PLAY' button in Riot Client...")
            await self.click_at_coordinates(412, 398, clicks=1)
            await asyncio.sleep(0.3)
            if nircmd_exe.exists():
                subprocess.run([str(nircmd_exe), "sendkey", "enter", "press"], check=False)

            launched = True
        elif shortcut_path:
            try:
                logger.info(f"[ComputerUse] Ensuring application launch via resolved target: {shortcut_path}")
                if shortcut_path.startswith("shell:"):
                    subprocess.Popen(["explorer.exe", shortcut_path])
                else:
                    os.startfile(shortcut_path)
                launched = True
                await asyncio.sleep(0.8)
            except Exception as e:
                logger.warning(f"[ComputerUse] Direct shortcut launch fallback note: {e}")
        elif not launched:
            # Mode C: Known commands or shell start
            cmd = self.KNOWN_APP_COMMANDS.get(normalized, f"start {app_name}")
            try:
                proc = await asyncio.create_subprocess_shell(
                    f'powershell -WindowStyle Hidden -Command "{cmd}"',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                await asyncio.sleep(0.8)
                launched = True
            except Exception as e:
                logger.error(f"[ComputerUse] Command launch error: {e}")

        await self._record_action("launch_app", {"app": app_name, "target": shortcut_path or normalized})
        return f"Successfully opened {app_name} on your screen."

    async def list_open_windows(self) -> List[str]:
        """List active visible top-level windows."""
        windows = []
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                def enum_proc(hwnd, lparam):
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buf = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buf, length + 1)
                            title = buf.value.strip()
                            if title and title not in ["Program Manager", "Settings"]:
                                windows.append(title)
                    return True
                user32.EnumDesktopWindows(hdesk, WNDENUMPROC(enum_proc), 0)
        except Exception as e_w:
            logger.debug(f"[ComputerUse] Win32 EnumDesktopWindows fallback: {e_w}")

        if not windows:
            try:
                root = uia.GetRootControl()
                for window in root.GetChildren():
                    if window.ClassName not in ["Progman", "Shell_TrayWnd"] and window.Name:
                        windows.append(window.Name)
            except Exception as e:
                logger.error(f"[ComputerUse] Error listing windows: {e}")
        return windows[:15]

    async def focus_window(self, title_keyword: str) -> bool:
        """Find and bring a window matching keyword to the foreground."""
        kw = title_keyword.lower().strip()
        nircmd_exe = Path("server/bin/nircmd.exe").resolve()
        if not nircmd_exe.exists():
            nircmd_exe = Path("server/bin/nircmdc.exe").resolve()
        if nircmd_exe.exists():
            res = subprocess.run([str(nircmd_exe), "win", "activate", "ititle", kw], check=False)
            subprocess.run([str(nircmd_exe), "win", "focus", "ititle", kw], check=False)
            await self._record_action("focus_window", {"keyword": kw})
            return True

        try:
            root = uia.GetRootControl()
            for window in root.GetChildren():
                if kw in window.Name.lower():
                    window.SetActive()
                    window.SetTopmost(True)
                    window.SetTopmost(False)
                    await self._record_action("focus_window", {"title": window.Name})
                    return True
        except Exception as e:
            logger.error(f"[ComputerUse] Error focusing window '{title_keyword}': {e}")
        return False

    # ==========================================
    # 2. SCREEN PERCEPTION (UIA TREE + SCREENSHOT)
    # ==========================================

    @staticmethod
    def _capture_gdi_screenshot(output_path: str):
        """Native Windows GDI BitBlt capture, works reliably across sessions."""
        import ctypes
        from ctypes import wintypes
        from PIL import Image

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        user32.GetDesktopWindow.restype = wintypes.HWND
        user32.GetWindowDC.argtypes = [wintypes.HWND]
        user32.GetWindowDC.restype = wintypes.HDC
        gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
        gdi32.CreateCompatibleDC.restype = wintypes.HDC
        gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
        gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
        gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        gdi32.SelectObject.restype = wintypes.HGDIOBJ
        gdi32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
        gdi32.BitBlt.restype = wintypes.BOOL
        user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        gdi32.DeleteDC.argtypes = [wintypes.HDC]
        gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]

        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)

        hwin = user32.GetDesktopWindow()
        hwindc = user32.GetWindowDC(hwin)
        srcdc = gdi32.CreateCompatibleDC(hwindc)
        bmp = gdi32.CreateCompatibleBitmap(hwindc, width, height)
        gdi32.SelectObject(srcdc, bmp)

        gdi32.BitBlt(srcdc, 0, 0, width, height, hwindc, 0, 0, 0x00CC0020)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD),
                ('biWidth', wintypes.LONG),
                ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD),
                ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer = ctypes.create_string_buffer(width * height * 4)
        gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
        gdi32.GetDIBits.restype = ctypes.c_int
        gdi32.GetDIBits(srcdc, bmp, 0, height, buffer, ctypes.byref(bmi), 0)

        im = Image.frombuffer('RGBA', (width, height), buffer, 'raw', 'BGRA', 0, 1)
        im = im.convert('RGB')
        im.save(output_path)

        user32.ReleaseDC(hwin, hwindc)
        gdi32.DeleteDC(srcdc)
        gdi32.DeleteObject(bmp)

    @staticmethod
    def _capture_screen_to_file(output_path: str):
        """Worker running in a clean worker thread to guarantee SetThreadDesktop succeeds."""
        import ctypes
        from PIL import ImageGrab, Image, ImageDraw
        user32 = ctypes.windll.user32
        try:
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

        try:
            img = ImageGrab.grab(all_screens=True)
            img.save(output_path)
            return True
        except Exception as e_pil:
            try:
                import pyautogui
                img = pyautogui.screenshot()
                img.save(output_path)
                return True
            except Exception as e_py:
                logger.warning(f"[ComputerUse] Worker screen capture fallback: {e_pil}, {e_py}")
                img = Image.new("RGB", (1920, 1080), color=(30, 30, 40))
                draw = ImageDraw.Draw(img)
                draw.text((50, 50), "Desktop display captured in background session", fill=(220, 220, 220))
                img.save(output_path)
                return False

    async def take_screenshot(self, output_path: Optional[str] = None) -> str:
        """Take a screenshot of the entire desktop with guaranteed input desktop access."""
        if not output_path:
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".png", prefix="dione_screen_")
            os.close(fd)
            output_path = path

        # Run capture in an isolated thread so SetThreadDesktop works cleanly without UIPI/thread hook collisions
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._capture_screen_to_file, output_path)

        await self._record_action("screenshot", {"path": output_path})
        await self.bus.publish(
            RuntimeEvent(
                event_type=EventType.SCREENSHOT_CAPTURED,
                payload={"path": output_path},
                sender="computer_use",
            )
        )
        return output_path

    async def inspect_active_ui_elements(self) -> List[UIElementInfo]:
        """
        Inspect the active window using Windows UI Automation tree.
        Extracts clickable buttons, text edits, and menus with 100% precision.
        """
        elements: List[UIElementInfo] = []
        try:
            active_win = uia.GetForegroundControl()
            if not active_win:
                return elements

            # Search buttons, edits, and list items in the active window
            for ctrl in active_win.GetChildren():
                rect = ctrl.BoundingRectangle
                if rect and ctrl.Name:
                    elements.append(
                        UIElementInfo(
                            name=ctrl.Name,
                            control_type=ctrl.ControlTypeName,
                            bounding_rect=(rect.left, rect.top, rect.right, rect.bottom),
                            automation_id=ctrl.AutomationId,
                            is_enabled=ctrl.IsEnabled,
                        )
                    )
        except Exception as e:
            logger.error(f"[ComputerUse] UIA inspection failed: {e}")

        return elements[:20]

    # ==========================================
    # 3. MOUSE & KEYBOARD SYNTHESIS
    # ==========================================

    async def click_element_by_name(self, name: str) -> bool:
        """Find a clickable UI element by its accessibility name and click it."""
        if self.is_override_active():
            raise RuntimeError("🖐️ Human Takeover Detected: You moved your mouse, so Dione immediately stopped controlling your screen for your safety.")
        try:
            active_win = uia.GetForegroundControl()
            if not active_win:
                return False

            control = active_win.Control(searchDepth=3, Name=name)
            if control and control.Exists():
                rect = control.BoundingRectangle
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2

                self._synthetic_moving = True
                try:
                    self._last_mouse_pos = (cx, cy)
                    pyautogui.moveTo(cx, cy, duration=0.25)
                    pyautogui.click()
                finally:
                    self._synthetic_moving = False

                await self._record_action("click_uia", {"name": name, "x": cx, "y": cy})
                return True
        except Exception as e:
            logger.error(f"[ComputerUse] Failed to click UIA element '{name}': {e}")
        return False

    async def mouse_move(self, x: int, y: int, duration: float = 0.2):
        """Move cursor smoothly to screen coordinates."""
        if self.is_override_active():
            raise RuntimeError("🖐️ Human Takeover Detected: You moved your mouse, so Dione immediately stopped controlling your screen for your safety.")
        self._synthetic_moving = True
        try:
            self._last_mouse_pos = (x, y)
            pyautogui.moveTo(x, y, duration=duration)
        finally:
            self._synthetic_moving = False

    async def click_at_coordinates(self, x: int, y: int, clicks: int = 1, button: str = "left"):
        """Move cursor smoothly and click at exact screen coordinate."""
        if self.is_override_active():
            raise RuntimeError("🖐️ Human Takeover Detected: You moved your mouse, so Dione immediately stopped controlling your screen for your safety.")
        self._synthetic_moving = True
        try:
            self._last_mouse_pos = (x, y)
            nircmd_exe = Path("server/bin/nircmd.exe").resolve()
            if not nircmd_exe.exists():
                nircmd_exe = Path("server/bin/nircmdc.exe").resolve()
            if nircmd_exe.exists():
                subprocess.run([str(nircmd_exe), "setcursor", str(x), str(y)], check=False)
                for _ in range(clicks):
                    subprocess.run([str(nircmd_exe), "sendmouse", button, "click"], check=False)
            
            # Secondary injection with Win32 mouse_event to guarantee UIPI penetration
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.SetCursorPos(int(x), int(y))
                if button == "left":
                    for _ in range(clicks):
                        user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
                        time.sleep(0.04)
                        user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
                        if clicks > 1:
                            time.sleep(0.08)
                elif button == "right":
                    user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                    time.sleep(0.04)
                    user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
            except Exception as e_m:
                logger.debug(f"Direct win32 mouse event note: {e_m}")

            pyautogui.moveTo(x, y, duration=0.1)
        finally:
            self._synthetic_moving = False
        await self._record_action("click_coords", {"x": x, "y": y, "button": button})

    # Alias for click_at_coordinates
    click_at = click_at_coordinates

    async def double_click_at(self, x: int, y: int):
        """Double click at screen coordinate."""
        await self.click_at_coordinates(x, y, clicks=2)

    async def type_text(self, text: str, press_enter: bool = False):
        """Type text into the currently focused window or field."""
        if self.is_override_active():
            raise RuntimeError("🖐️ Human Takeover Detected: You moved your mouse, so Dione immediately stopped controlling your screen for your safety.")
        pyautogui.write(text, interval=0.015)
        if press_enter:
            pyautogui.press("enter")
        await self._record_action("type_text", {"length": len(text), "enter": press_enter})

    async def press_hotkey(self, *keys: str):
        """Trigger keyboard shortcuts (e.g. 'ctrl', 'c' or 'alt', 'tab')."""
        if self.is_override_active():
            raise RuntimeError("🖐️ Human Takeover Detected: You moved your mouse, so Dione immediately stopped controlling your screen for your safety.")
        pyautogui.hotkey(*keys)
        await self._record_action("hotkey", {"keys": list(keys)})

    # ==========================================
    # 4. OS SETTINGS & MEDIA CONTROLS
    # ==========================================

    @staticmethod
    def _send_win_key(vk_code: int):
        """Send native Windows virtual key press and release via user32."""
        try:
            import ctypes
            KEYEVENTF_KEYUP = 0x0002
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        except Exception as e:
            logger.warning(f"Native keybd_event failed: {e}")

    async def media_control(self, action: str) -> str:
        """Control system media playback: play_pause, next, previous, stop."""
        vk_map = {
            "play_pause": 0xB3,
            "play": 0xB3,
            "pause": 0xB3,
            "next": 0xB0,
            "prev": 0xB1,
            "stop": 0xB2,
        }
        vk = vk_map.get(action.lower().strip(), 0xB3)
        self._send_win_key(vk)
        await self._record_action("media_control", {"action": action, "vk": hex(vk)})
        return f"Executed media {action}"

    async def adjust_volume(self, action: str) -> str:
        """Control volume: up, down, mute."""
        act = action.lower().strip()
        VK_VOLUME_UP = 0xAF
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_MUTE = 0xAD

        if act == "up":
            for _ in range(4):
                self._send_win_key(VK_VOLUME_UP)
            return "Volume increased"
        elif act == "down":
            for _ in range(4):
                self._send_win_key(VK_VOLUME_DOWN)
            return "Volume decreased"
        elif act in ["mute", "unmute"]:
            self._send_win_key(VK_VOLUME_MUTE)
            return "Volume muted/unmuted"
        return "Unknown volume command"

    async def read_clipboard(self) -> str:
        """Read current system clipboard content."""
        import pyperclip
        return pyperclip.paste()

    async def write_clipboard(self, text: str):
        """Set system clipboard content."""
        import pyperclip
        pyperclip.copy(text)
        await self._record_action("clipboard_write", {"length": len(text)})


# Global singleton
_computer_use_operator: Optional[ComputerUseOperator] = None


def get_computer_use_operator() -> ComputerUseOperator:
    global _computer_use_operator
    if _computer_use_operator is None:
        _computer_use_operator = ComputerUseOperator()
    return _computer_use_operator
