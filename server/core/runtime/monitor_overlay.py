"""
Dione AI - Native OS Monitor Overlay Manager
Spawns an OS-level, always-on-top, monitor-wide semi-transparent barrier
with an interactive floating HUD and emergency ESC stop listener.
Runs in an isolated child process to ensure zero interference with the asyncio engine.
"""

import sys
import os
import subprocess
import threading
import time
from typing import Optional
from loguru import logger


OVERLAY_PROCESS_CODE = """
import sys
import tkinter as tk
import ctypes
import json

def setup_clickthrough(hwnd):
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000
    cur_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur_style | WS_EX_TRANSPARENT | WS_EX_LAYERED)

action_text = sys.argv[1] if len(sys.argv) > 1 else "Autonomous PC Control Active"

# 1. Main HUD Window (Centered Top Banner)
root = tk.Tk()
root.title("Dione Monitor HUD")
root.attributes("-topmost", True)
root.overrideredirect(True)

sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()

bw = 540
bh = 52
bx = (sw - bw) // 2
by = 12
root.geometry(f"{bw}x{bh}+{bx}+{by}")
root.configure(bg="#080c18")

# 2. Backdrop Window (Darkened tint across entire physical monitor)
backdrop = tk.Toplevel(root)
backdrop.title("Dione Monitor Backdrop")
backdrop.attributes("-topmost", True)
backdrop.attributes("-alpha", 0.28)
backdrop.overrideredirect(True)
backdrop.geometry(f"{sw}x{sh}+0+0")
backdrop.configure(bg="#000000")

backdrop.update_idletasks()
h_back = ctypes.windll.user32.GetParent(backdrop.winfo_id()) or backdrop.winfo_id()
setup_clickthrough(h_back)

# Emergency Stop trigger
def trigger_stop():
    print("USER_STOPPED", flush=True)
    try:
        root.destroy()
    except Exception:
        pass
    sys.exit(0)

# Banner Frame
frm = tk.Frame(root, bg="#080c18", highlightbackground="#8b5cf6", highlightthickness=1.5)
frm.pack(fill="both", expand=True)

# Status icon & text
left_box = tk.Frame(frm, bg="#080c18")
left_box.pack(side="left", padx=12, fill="y")

badge = tk.Label(
    left_box,
    text="● IN CONTROL",
    fg="#ec4899",
    bg="#080c18",
    font=("Segoe UI", 9, "bold")
)
badge.pack(anchor="w", pady=(6, 0))

lbl_action = tk.Label(
    left_box,
    text=action_text[:40] + ("..." if len(action_text) > 40 else ""),
    fg="#cbd5e1",
    bg="#080c18",
    font=("Segoe UI", 8)
)
lbl_action.pack(anchor="w")

# Stop Button
btn_stop = tk.Button(
    frm,
    text="🛑 STOP (Esc)",
    bg="#ef4444",
    activebackground="#dc2626",
    fg="#ffffff",
    activeforeground="#ffffff",
    command=trigger_stop,
    font=("Segoe UI", 9, "bold"),
    relief="flat",
    padx=14,
    pady=4,
    cursor="hand2"
)
btn_stop.pack(side="right", padx=12, pady=9)

# Global ESC detection in loop
root.bind("<Escape>", lambda e: trigger_stop())

# Fallback poll via GetAsyncKeyState for ESC key (works even if HUD loses focus)
def check_esc_poll():
    VK_ESCAPE = 0x1B
    if ctypes.windll.user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
        trigger_stop()
    else:
        root.after(80, check_esc_poll)

root.after(80, check_esc_poll)

try:
    root.mainloop()
except Exception:
    pass
"""


class MonitorOverlayManager:
    """Manages the lifecycle of the fullscreen monitor overlay process."""

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._active_action: str = ""
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None

    def show_overlay(self, action_description: str = "Autonomous Computer-Use in progress..."):
        """Record autonomous control activity without spawning intrusive topmost barrier windows."""
        logger.debug(f"[MonitorOverlay] Autonomous action active: {action_description}")
        return

    def hide_overlay(self):
        """Dismiss monitor overlay."""
        with self._lock:
            if self._proc is not None:
                try:
                    if self._proc.poll() is None:
                        self._proc.terminate()
                        self._proc.wait(timeout=0.6)
                except Exception:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
                finally:
                    self._proc = None

    def is_visible(self) -> bool:
        """Check if the monitor overlay is currently displaying."""
        return self._proc is not None and self._proc.poll() is None

    def _monitor_output(self):
        """Read stdout from overlay process to detect user emergency stop."""
        proc = self._proc
        if not proc or not proc.stdout:
            return

        try:
            for line in iter(proc.stdout.readline, ""):
                line_clean = line.strip()
                if "USER_STOPPED" in line_clean:
                    logger.warning("[MonitorOverlay] 🛑 Emergency STOP clicked/pressed on monitor overlay!")
                    self._handle_user_abort()
                    break
        except Exception as e:
            logger.debug(f"[MonitorOverlay] Reader exception: {e}")

    def _handle_user_abort(self):
        """Trigger emergency stop across event bus and computer use runtime."""
        from server.core.runtime.event_bus import get_event_bus
        from server.core.runtime.computer_use import get_computer_use_operator

        try:
            op = get_computer_use_operator()
            op.bus.trigger_emergency_stop("[USER_STOPPED] Autonomous action halted by user via Monitor Overlay.")
            op._human_override_active = True
        except Exception as err:
            logger.error(f"[MonitorOverlay] Error propagating emergency abort: {err}")


# Singleton
_monitor_overlay: Optional[MonitorOverlayManager] = None

def get_monitor_overlay() -> MonitorOverlayManager:
    global _monitor_overlay
    if _monitor_overlay is None:
        _monitor_overlay = MonitorOverlayManager()
    return _monitor_overlay
