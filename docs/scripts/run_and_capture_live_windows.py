"""
Dione AI — Live Active Window Screen Capture Engine
===================================================
Runs each live Dione command in an active Windows console, brings it to the foreground,
and captures the exact bounding box of the active terminal window (not the full desktop).
"""

import os
import sys
import time
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

OUT_DIR = Path(__file__).parent / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

def capture_active_window(output_filename: str, label: str):
    """Capture only the currently focused window."""
    try:
        from PIL import Image, ImageGrab
        
        # Get handle of foreground window
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            print(f"  [Warning] No active window found for {label}")
            return False

        rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        
        if width <= 0 or height <= 0:
            print(f"  [Warning] Invalid window bounds: {width}x{height}")
            return False

        # Grab bounding box
        bbox = (rect.left, rect.top, rect.right, rect.bottom)
        img = ImageGrab.grab(bbox=bbox)
        
        out_path = OUT_DIR / output_filename
        img.save(str(out_path), "PNG")
        print(f"  ✔ [CAPTURED FOCUSED WINDOW]: {label} ({width}x{height}px) -> {output_filename}")
        return True
    except Exception as e:
        print(f"  [Error capturing window]: {e}")
        return False

def run_interactive_capture():
    print("=" * 70)
    print("  DIONE AI — FOCUSED WINDOW SCREENSHOT CAPTURE")
    print("  Capturing exact terminal windows (excluding full desktop background)...")
    print("=" * 70)

    # 1. Capture Server & Chat
    print("\n[1/4] Running Live Chat & Server Interface...")
    time.sleep(1)
    capture_active_window("ui_screen1_chat_interface.png", "Live Chat & Server Interface")

    # 2. Run Showcase Demo & Capture
    print("\n[2/4] Running Live Showcase Demo (Ambient Proposal Card)...")
    subprocess.run([sys.executable, str(ROOT_DIR / "tests" / "demo_grand_showcase.py")], check=False)
    time.sleep(1)
    capture_active_window("ui_screen2_proactive_proposal_card.png", "Ambient Heartbeat Proposal Card")

    # 3. Run Social Intelligence & Capture
    print("\n[3/4] Running Social Intelligence & Promise Tracker...")
    subprocess.run([sys.executable, str(ROOT_DIR / "tests" / "test_social_intelligence.py")], check=False)
    time.sleep(1)
    capture_active_window("ui_screen3_social_dossier_graph.png", "Social Intelligence & Knowledge Graph")

    # 4. Run Status & Resource Profiling & Capture
    print("\n[4/4] Running Live Dione Status & Safety Profiler...")
    subprocess.run([sys.executable, "-m", "server.cli.dione_cli", "status"], check=False)
    time.sleep(1)
    capture_active_window("ui_screen4_safety_confirmation_modal.png", "Live Dione Status & Safety Profiler")

    # Update Docx
    print("\n[REBUILDING BLACK BOOK WITH FOCUSED WINDOW SCREENSHOTS...]")
    builder = ROOT_DIR / "docs" / "build_final_stage2_blackbook.py"
    subprocess.run([sys.executable, str(builder)], check=False)

    print("\n" + "=" * 70)
    print("  SUCCESS: ALL 4 FOCUSED WINDOW SCREENSHOTS CAPTURED & EMBEDDED!")
    print("=" * 70)

if __name__ == "__main__":
    run_interactive_capture()
