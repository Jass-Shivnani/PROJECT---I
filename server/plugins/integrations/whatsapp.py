"""
WhatsApp Business/Bridge Integration Plugin
"""

from __future__ import annotations

import os
import sys
import json
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger
import httpx

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration


class WhatsAppIntegration(BaseIntegration):
    """
    WhatsApp Web integration via local Node.js Baileys bridge.

    Uses QR login (no Business API required).
    """
    
    INTEGRATION_ID = "whatsapp"
    DISPLAY_NAME = "WhatsApp"
    DESCRIPTION = "Send and receive WhatsApp messages via WhatsApp Web"
    AUTH_TYPE = AuthType.DEVICE_CODE
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = ["whatsapp_web"]

    def _bridge_from_credentials(self):
        if not self.credentials:
            return None

        from server.whatsapp import get_bridge

        bridge_port = int(self.credentials.extra.get("bridge_port", 8901))
        dione_port = int(self.credentials.extra.get("dione_port", 8900))
        allowed_chat_id = str(self.credentials.extra.get("allowed_chat_id", "")).strip()
        allowed_number = str(self.credentials.extra.get("allowed_number", "")).strip()
        return get_bridge(
            dione_port=dione_port,
            bridge_port=bridge_port,
            allowed_chat_id=allowed_chat_id,
            allowed_number=allowed_number,
        )

    def _ensure_bridge_started(self) -> bool:
        bridge = self._bridge_from_credentials()
        if bridge is None:
            return False
        return bridge.start()
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        try:
            import shutil
            from server.whatsapp import get_bridge

            dione_port = int(params.get("dione_port", 8900))
            bridge_port = int(params.get("bridge_port", 8901))
            allowed_chat_id = str(params.get("allowed_chat_id", "")).strip()
            allowed_number = str(params.get("allowed_number", "")).strip()
            bridge = get_bridge(
                dione_port=dione_port,
                bridge_port=bridge_port,
                allowed_chat_id=allowed_chat_id,
                allowed_number=allowed_number,
            )

            if bool(params.get("reset_session", False)):
                try:
                    bridge.stop()
                except Exception:
                    pass
                auth_dir = Path("data") / "whatsapp_auth"
                if auth_dir.exists():
                    shutil.rmtree(auth_dir, ignore_errors=True)

            started = bridge.start()
            if not started:
                return False

            self.credentials = IntegrationCredentials(
                integration_id=self.INTEGRATION_ID,
                auth_type=AuthType.DEVICE_CODE,
                extra={
                    "mode": "web_bridge",
                    "bridge_port": bridge_port,
                    "dione_port": dione_port,
                    "allowed_chat_id": allowed_chat_id,
                    "allowed_number": allowed_number,
                },
            )
            return True
        except Exception as e:
            logger.error(f"WhatsApp web bridge auth failed: {e}")
            return False
    
    async def test_connection(self) -> bool:
        if not self.credentials:
            return False
        try:
            from server.whatsapp import get_bridge
            bridge_port = int(self.credentials.extra.get("bridge_port", 8901))
            dione_port = int(self.credentials.extra.get("dione_port", 8900))
            bridge = get_bridge(dione_port=dione_port, bridge_port=bridge_port)
            if not bridge.is_running:
                return False
            status = await bridge.get_status()
            # ONLY return True if mobile device is actively connected and logged in
            # If status is "qr", "disconnected", or logged out from mobile, return False
            return status.get("status") == "connected"
        except Exception:
            return False
    
    async def sync(self) -> dict[str, Any]:
        if not self.credentials:
            return {"status": "disconnected"}
        try:
            if not self._ensure_bridge_started():
                return {"status": "bridge_not_running", "has_qr": False}
            bridge = self._bridge_from_credentials()
            if bridge is None:
                return {"status": "bridge_not_running", "has_qr": False}

            status = await bridge.get_status()
            if status.get("status") == "connecting":
                for _ in range(8):
                    await asyncio.sleep(0.5)
                    status = await bridge.get_status()
                    if status.get("status") in {"connected", "qr", "disconnected", "error"}:
                        break

            qr = await bridge.get_qr()
            return {
                "status": status.get("status", "unknown"),
                "has_qr": bool(qr.get("qr")),
                "bridge": status,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_qr(self) -> dict:
        if not self.credentials:
            return {"status": "disconnected", "qr": None}
        try:
            if not self._ensure_bridge_started():
                return {"status": "bridge_not_running", "qr": None}
            bridge = self._bridge_from_credentials()
            if bridge is None:
                return {"status": "bridge_not_running", "qr": None}
            return await bridge.get_qr()
        except Exception as e:
            return {"status": "error", "error": str(e), "qr": None}
    
    async def send_message(
        self,
        to: str,
        chat_id: str = "",
        text: str = "",
        file_path: str = "",
        caption: str = "",
        mime_type: str = "",
    ) -> dict:
        """Send a WhatsApp text or file message via bridge."""
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}
        try:
            if not self._ensure_bridge_started():
                return {"success": False, "error": "Bridge not running"}
            bridge = self._bridge_from_credentials()
            if bridge is None:
                return {"success": False, "error": "Bridge not running"}

            status = await bridge.get_status()
            if status.get("status") != "connected":
                for _ in range(15):
                    await asyncio.sleep(1)
                    status = await bridge.get_status()
                    if status.get("status") == "connected":
                        break

            if status.get("status") != "connected":
                if status.get("status") == "qr":
                    return {"success": False, "error": "WhatsApp requires QR login before sending"}
                return {"success": False, "error": f"WhatsApp not connected (status={status.get('status', 'unknown')})"}

            result = await bridge.send_message(
                to=to,
                chat_id=chat_id,
                text=text,
                file_path=file_path,
                caption=caption,
                mime_type=mime_type,
            )
            if result.get("error"):
                return {"success": False, "error": result.get("error")}
            return {"success": bool(result.get("ok", False)), "response": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "whatsapp_send",
                "description": "Send a WhatsApp message or file",
                "parameters": {
                    "to": {"type": "string", "description": "Phone number (with country code)"},
                    "chat_id": {"type": "string", "description": "Optional WhatsApp chat JID (preferred for in-channel replies)"},
                    "text": {"type": "string", "description": "Message text (optional if sending a file)"},
                    "file_path": {"type": "string", "description": "Optional local file path to send"},
                    "file_query": {"type": "string", "description": "Optional filename/path search query to auto-find file"},
                    "search_root": {"type": "string", "description": "Optional root directory for file_query"},
                    "caption": {"type": "string", "description": "Optional caption for the file"},
                    "mime_type": {"type": "string", "description": "Optional MIME type override (example: image/png)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "whatsapp_send_file",
                "description": "Send an actual local file over WhatsApp (not file contents)",
                "parameters": {
                    "to": {"type": "string", "description": "Phone number (with country code)"},
                    "chat_id": {"type": "string", "description": "Optional WhatsApp chat JID (preferred for in-channel replies)"},
                    "file_path": {"type": "string", "description": "Local file path to send"},
                    "file_query": {"type": "string", "description": "Optional filename/path search query if file_path unknown"},
                    "search_root": {"type": "string", "description": "Optional root directory for file_query"},
                    "caption": {"type": "string", "description": "Optional caption"},
                    "mime_type": {"type": "string", "description": "Optional MIME type override"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]


# ─── Telegram Integration ────────────────────────────────────
