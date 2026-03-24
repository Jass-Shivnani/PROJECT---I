"""
Dione AI — WhatsApp Web Bridge Manager

Manages the Node.js Baileys bridge process that connects to WhatsApp Web.
Architecture:

    WhatsApp ←→ Baileys (Node.js) ←→ HTTP ←→ FastAPI (Python)

The bridge runs as a child process on a local port (default 8901).
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional
from loguru import logger

import httpx


DEFAULT_BRIDGE_PORT = 8901
BRIDGE_DIR = Path(__file__).parent
BRIDGE_SCRIPT = BRIDGE_DIR / "bridge.js"
NODE_MODULES = BRIDGE_DIR / "node_modules"


def _get_auth_dir():
    return Path("data") / "whatsapp_auth"


AUTH_DIR_DEFAULT = _get_auth_dir()


def find_node() -> Optional[str]:
    return shutil.which("node")


def find_npm() -> Optional[str]:
    return shutil.which("npm")


def is_deps_installed() -> bool:
    return NODE_MODULES.exists() and (NODE_MODULES / "@whiskeysockets").exists()


def install_deps() -> bool:
    npm = find_npm()
    if not npm:
        logger.error("npm not found — cannot install WhatsApp bridge dependencies")
        return False

    logger.info("Installing WhatsApp bridge dependencies (first time only)...")
    try:
        result = subprocess.run(
            [npm, "install", "--production"],
            cwd=str(BRIDGE_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error(f"npm install failed: {result.stderr}")
            return False
        logger.info("WhatsApp bridge dependencies installed")
        return True
    except subprocess.TimeoutExpired:
        logger.error("npm install timed out (120s)")
        return False
    except Exception as e:
        logger.error(f"npm install error: {e}")
        return False


class WhatsAppBridge:
    """Manages the Node.js WhatsApp-Baileys bridge subprocess."""

    def __init__(
        self,
        dione_port: int = 8900,
        bridge_port: int = DEFAULT_BRIDGE_PORT,
        auth_dir: Optional[str] = None,
        allowed_chat_id: str = "",
        allowed_number: str = "",
    ):
        self.dione_port = dione_port
        self.bridge_port = bridge_port
        self.auth_dir = auth_dir or str(AUTH_DIR_DEFAULT)
        self.allowed_chat_id = allowed_chat_id.strip()
        self.allowed_number = allowed_number.replace("+", "").strip()
        self._process: Optional[subprocess.Popen] = None
        self._running = False

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.bridge_port}"

    @property
    def is_running(self) -> bool:
        return self._running and self._process is not None and self._process.poll() is None

    def _is_bridge_responsive(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/status", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def start(self) -> bool:
        if self.is_running or self._is_bridge_responsive():
            logger.info(f"WhatsApp bridge already running on port {self.bridge_port}")
            return True

        node = find_node()
        if not node:
            logger.error("Node.js not found. Install Node.js to use WhatsApp: https://nodejs.org")
            return False

        if not BRIDGE_SCRIPT.exists():
            logger.error(f"Bridge script not found: {BRIDGE_SCRIPT}")
            return False

        if not is_deps_installed() and not install_deps():
            return False

        env = {
            **os.environ,
            "DIONE_PORT": str(self.dione_port),
            "BRIDGE_PORT": str(self.bridge_port),
            "WA_AUTH_DIR": str(Path(self.auth_dir).resolve()),
            "LOG_LEVEL": "warn",
        }
        if self.allowed_chat_id:
            env["WA_ALLOWED_CHAT_ID"] = self.allowed_chat_id
        if self.allowed_number:
            env["WA_ALLOWED_NUMBER"] = self.allowed_number

        try:
            self._process = subprocess.Popen(
                [node, str(BRIDGE_SCRIPT)],
                cwd=str(BRIDGE_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            self._running = True

            import threading
            threading.Thread(target=self._read_logs, daemon=True, name="wa-bridge-logs").start()

            for _ in range(30):
                time.sleep(0.5)
                if not self.is_running:
                    logger.error("WhatsApp bridge process died during startup")
                    return False
                if self._is_bridge_responsive():
                    logger.info(f"WhatsApp bridge started on port {self.bridge_port}")
                    return True

            logger.error("WhatsApp bridge did not respond within 15s")
            self.stop()
            return False
        except Exception as e:
            logger.error(f"Failed to start WhatsApp bridge: {e}")
            return False

    def stop(self):
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception:
                pass
            self._process = None
        logger.info("WhatsApp bridge stopped")

    def _read_logs(self):
        try:
            while self._running and self._process and self._process.stdout:
                line = self._process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    logger.info(f"[wa-bridge] {line}")
        except Exception:
            pass

    async def get_status(self) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/status", timeout=5)
                return resp.json()
        except Exception as e:
            if not self.is_running:
                return {"status": "bridge_not_running"}
            return {"status": "error", "error": str(e)}

    async def get_qr(self) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/qr", timeout=5)
                return resp.json()
        except Exception as e:
            if not self.is_running:
                return {"qr": None, "status": "bridge_not_running"}
            return {"qr": None, "status": "error", "error": str(e)}

    async def send_message(self, to: str, text: str, chat_id: str = "") -> dict:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/send",
                    json={"to": to, "text": text, "chat_id": chat_id},
                    timeout=15,
                )
                return resp.json()
        except Exception as e:
            if not self.is_running:
                return {"error": "Bridge not running"}
            return {"error": str(e)}

    async def logout(self) -> dict:
        if not self.is_running:
            return {"error": "Bridge not running"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.base_url}/logout", timeout=10)
                return resp.json()
        except Exception as e:
            return {"error": str(e)}


_bridge_instance: Optional[WhatsAppBridge] = None


def get_bridge(
    dione_port: int = 8900,
    bridge_port: int = DEFAULT_BRIDGE_PORT,
    allowed_chat_id: str = "",
    allowed_number: str = "",
) -> WhatsAppBridge:
    global _bridge_instance
    needs_new = (
        _bridge_instance is None
        or _bridge_instance.dione_port != dione_port
        or _bridge_instance.bridge_port != bridge_port
        or _bridge_instance.allowed_chat_id != allowed_chat_id.strip()
        or _bridge_instance.allowed_number != allowed_number.replace("+", "").strip()
    )

    if needs_new:
        if _bridge_instance and _bridge_instance.is_running:
            _bridge_instance.stop()
        _bridge_instance = WhatsAppBridge(
            dione_port=dione_port,
            bridge_port=bridge_port,
            allowed_chat_id=allowed_chat_id,
            allowed_number=allowed_number,
        )
    return _bridge_instance
