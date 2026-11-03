"""
Dione AI — Sovereign Native Desktop Application & System Tray
=============================================================
A native desktop app for Windows powered by Microsoft Edge WebView2 & pystray:
1. Spawns the sovereign backend in a dedicated background subprocess.
2. Creates an authentic 1400x880 native desktop app window (zero browser tabs/chrome).
3. Provides a live Windows System Tray icon with quick actions:
   - Show/Restore Dione Assistant
   - Trigger Autonomous Dream & Scout Cycle
   - Quit Dione Completely
4. Minimizes seamlessly to tray on window close.
"""

import sys
import os
import time
import subprocess
import threading
import urllib.request
from pathlib import Path

# Windows event loop policy
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw
import webview
import pystray
from pystray import MenuItem as item
from loguru import logger

SPLASH_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Dione AI</title>
<style>
  body {
    background: #05060b;
    color: #f1f5f9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    margin: 0;
    user-select: none;
    -webkit-user-select: none;
  }
  .orb {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: radial-gradient(circle, #38bdf8 0%, #818cf8 50%, #4f46e5 100%);
    box-shadow: 0 0 32px rgba(99, 102, 241, 0.6);
    animation: pulse 2s ease-in-out infinite alternate;
    margin-bottom: 28px;
  }
  @keyframes pulse {
    0% { transform: scale(0.92); opacity: 0.8; box-shadow: 0 0 20px rgba(99, 102, 241, 0.4); }
    100% { transform: scale(1.08); opacity: 1; box-shadow: 0 0 45px rgba(56, 189, 248, 0.8); }
  }
  h2 {
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.02em;
    margin: 0 0 8px 0;
    color: #f8fafc;
  }
  p {
    color: #94a3b8;
    font-size: 14px;
    margin: 0 0 20px 0;
  }
  .bar-container {
    width: 240px;
    height: 3px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
  }
  .bar {
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, #38bdf8, #818cf8, #a855f7);
    border-radius: 2px;
    position: absolute;
    animation: loading 1.8s ease-in-out infinite;
  }
  @keyframes loading {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
</style>
</head>
<body>
  <div class="orb"></div>
  <h2>Dione AI Sovereign Assistant</h2>
  <p id="status-msg">Initializing local neural core...</p>
  <div class="bar-container">
    <div class="bar"></div>
  </div>
  <script>
    const targetUrl = 'http://127.0.0.1:8900';
    function checkBackend() {
      fetch(targetUrl + '/api/health')
        .then(res => {
          if (res.ok) {
            document.getElementById('status-msg').innerText = 'Neural core online. Connecting...';
            window.location.href = targetUrl;
          } else {
            setTimeout(checkBackend, 600);
          }
        })
        .catch(() => {
          setTimeout(checkBackend, 600);
        });
    }
    setTimeout(checkBackend, 800);
  </script>
</body>
</html>
"""


def generate_tray_icon() -> Image.Image:
    """Generate a high-res celestial purple/cyan iris icon for the Windows system tray."""
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Outer violet ring
    draw.ellipse((4, 4, 60, 60), fill=(109, 40, 217, 255), outline=(139, 92, 246, 255), width=2)
    # Inner glowing cyan core
    draw.ellipse((16, 16, 48, 48), fill=(6, 182, 212, 255), outline=(103, 232, 249, 255), width=2)
    # Central white pupil
    draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 255))
    return img


class DioneNativeDesktopApp:
    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.tray_icon = None
        self.window = None
        self.is_running = True

    def start_backend_server(self):
        """Start the FastAPI uvicorn server in a dedicated background subprocess."""
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "server.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8900",
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self.server_process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                creationflags=flags,
            )
            logger.info(f"[NativeApp] Subprocess server spawned (PID={self.server_process.pid}) on 127.0.0.1:8900")
        except Exception as e:
            logger.error(f"[NativeApp] Failed to spawn backend subprocess: {e}")

    def wait_for_backend(self, timeout: float = 45.0) -> bool:
        """Wait until http://127.0.0.1:8900/api/health responds with 200 OK."""
        logger.info("[NativeApp] Waiting for sovereign neural backend to report healthy...")
        start_t = time.time()
        while time.time() - start_t < timeout:
            if self.server_process and self.server_process.poll() is not None:
                logger.error(f"[NativeApp] Backend subprocess terminated unexpectedly with code {self.server_process.returncode}")
                return False
            try:
                with urllib.request.urlopen("http://127.0.0.1:8900/api/health", timeout=1.5) as resp:
                    if resp.status == 200:
                        logger.info(f"[NativeApp] Backend verified healthy after {time.time() - start_t:.1f}s.")
                        return True
            except Exception:
                time.sleep(0.5)
        logger.warning("[NativeApp] Backend health check timeout reached; launching with dynamic splash loader.")
        return False

    def on_show_window(self, icon=None, item=None):
        """Restore and bring the Dione native window to the foreground."""
        if self.window:
            self.window.show()
            self.window.restore()

    def on_hide_window(self, icon=None, item=None):
        """Hide Dione window to the system tray."""
        if self.window:
            self.window.hide()

    def on_trigger_dream(self, icon=None, item=None):
        """Trigger an autonomous Dream & Scout cycle in the background."""
        def _do_trigger():
            try:
                req = urllib.request.Request("http://127.0.0.1:8900/api/ag-ui/briefing/trigger", method="POST")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    logger.info("[NativeApp] Dream & Scout cycle manually triggered from system tray.")
            except Exception as e:
                logger.error(f"[NativeApp] Failed to trigger dream cycle: {e}")

        threading.Thread(target=_do_trigger, daemon=True).start()

    def on_quit(self, icon=None, item=None):
        """Quit the desktop application, terminate backend process, and stop the system tray."""
        self.is_running = False
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        if self.server_process and self.server_process.poll() is None:
            logger.info(f"[NativeApp] Terminating backend subprocess PID={self.server_process.pid}...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
            except Exception:
                try:
                    self.server_process.kill()
                except Exception:
                    pass
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
        os._exit(0)

    def setup_tray(self):
        """Initialize the Windows system tray icon and menu."""
        menu = pystray.Menu(
            item("Open Dione Assistant", self.on_show_window, default=True),
            item("Trigger Scout Cycle (Dream Mode)", self.on_trigger_dream),
            pystray.Menu.SEPARATOR,
            item("Minimize to Tray", self.on_hide_window),
            item("Quit Dione", self.on_quit),
        )
        self.tray_icon = pystray.Icon(
            "Dione",
            generate_tray_icon(),
            "Dione AI — Sovereign Personal Assistant",
            menu=menu
        )
        threading.Thread(target=self.tray_icon.run, daemon=True, name="DioneTrayThread").start()
        logger.info("[NativeApp] Windows system tray icon registered.")

    def run(self):
        # 1. Start backend in background if not already running on port 8900
        backend_already_live = False
        try:
            with urllib.request.urlopen("http://127.0.0.1:8900/api/health", timeout=1.0) as resp:
                backend_already_live = (resp.status == 200)
        except Exception:
            backend_already_live = False

        backend_ready = False
        if not backend_already_live:
            self.start_backend_server()
            backend_ready = self.wait_for_backend(timeout=45.0)
        else:
            logger.info("[NativeApp] Connected to existing Dione backend on port 8900.")
            backend_ready = True

        # 2. Setup System Tray
        self.setup_tray()

        # 3. Create Native Desktop Window (powered by Edge WebView2)
        target_url = "http://127.0.0.1:8900" if backend_ready else None
        html_content = None if backend_ready else SPLASH_HTML

        self.window = webview.create_window(
            title="Dione AI — Sovereign Personal Assistant",
            url=target_url,
            html=html_content,
            width=1400,
            height=880,
            min_size=(1024, 700),
            resizable=True,
            background_color="#05060b",
        )

        # Hook window closing to minimize to tray instead of quitting
        def on_closing():
            self.window.hide()
            return False  # Prevent window destruction

        self.window.events.closing += on_closing

        logger.info("[NativeApp] Launching native Windows application window...")
        webview.start()


if __name__ == "__main__":
    app = DioneNativeDesktopApp()
    app.run()
