"""
Telegram Bot API Integration Plugin
"""

from __future__ import annotations

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger
import httpx

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration


class TelegramIntegration(BaseIntegration):
    """
    Telegram Bot API Integration.
    
    Provides high-reliability, cloud-native messaging without fragile browser bridges:
      - Send instant text messages and notifications
      - Send local files, reports, and photos
      - Read incoming messages and handle two-way chat
      - Zero Node.js / Puppeteer dependencies; 100% async Python (httpx)
    """

    INTEGRATION_ID = "telegram"
    DISPLAY_NAME = "Telegram"
    DESCRIPTION = "Send and receive messages and files via official Telegram Bot API"
    AUTH_TYPE = AuthType.TOKEN
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = ["bot_api"]

    API_BASE = "https://api.telegram.org"

    def _get_token(self) -> str:
        if not self.credentials:
            return os.getenv("DIONE_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
        return self.credentials.access_token or self.credentials.extra.get("bot_token", "")

    def _get_default_chat_id(self) -> str:
        if not self.credentials:
            return os.getenv("DIONE_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or ""
        return self.credentials.extra.get("chat_id") or self.credentials.extra.get("default_chat_id") or os.getenv("TELEGRAM_CHAT_ID", "")

    async def authenticate(self, params: dict[str, Any]) -> bool:
        token = str(
            params.get("bot_token")
            or params.get("token")
            or params.get("access_token")
            or ""
        ).strip()
        chat_id = str(params.get("chat_id") or params.get("default_chat_id") or "").strip()

        if not token:
            token = self._get_token()
        if not chat_id:
            chat_id = self._get_default_chat_id()

        if not token:
            logger.error("Telegram authentication failed: bot_token is required")
            return False

        self.credentials = IntegrationCredentials(
            integration_id=self.INTEGRATION_ID,
            auth_type=AuthType.TOKEN,
            access_token=token,
            extra={"chat_id": chat_id, "default_chat_id": chat_id},
        )

        return await self.test_connection()

    async def test_connection(self) -> bool:
        token = self._get_token()
        if not token:
            return False
        try:
            url = f"{self.API_BASE}/bot{token}/getMe"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return bool(data.get("ok"))
        except Exception as e:
            logger.error(f"Telegram test connection error: {e}")
        return False

    async def sync(self) -> dict[str, Any]:
        """Fetch bot info and recent updates."""
        token = self._get_token()
        if not token:
            return {"error": "Not authenticated"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.API_BASE}/bot{token}/getMe")
                if resp.status_code != 200:
                    return {"error": f"Failed to getMe: {resp.text}"}
                bot_info = resp.json().get("result", {})

                updates_resp = await client.get(f"{self.API_BASE}/bot{token}/getUpdates?limit=5")
                updates = updates_resp.json().get("result", []) if updates_resp.status_code == 200 else []

                return {
                    "bot_username": bot_info.get("username"),
                    "bot_name": bot_info.get("first_name"),
                    "recent_updates_count": len(updates),
                    "default_chat_id": self._get_default_chat_id(),
                }
        except Exception as e:
            return {"error": str(e)}

    async def send_message(self, text: str, chat_id: str = "") -> dict:
        """Send a text message via Telegram."""
        token = self._get_token()
        target_chat = chat_id.strip() or self._get_default_chat_id()
        if not token:
            return {"success": False, "error": "Telegram bot_token not configured"}
        if not target_chat:
            return {"success": False, "error": "chat_id is required (provide chat_id or set default_chat_id)"}

        try:
            url = f"{self.API_BASE}/bot{token}/sendMessage"
            payload = {
                "chat_id": target_chat,
                "text": text,
                "parse_mode": "Markdown",
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return {"success": True, "result": resp.json().get("result")}
                elif resp.status_code == 400:
                    payload.pop("parse_mode", None)
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        return {"success": True, "result": resp.json().get("result")}
                return {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_file(self, file_path: str, chat_id: str = "", caption: str = "") -> dict:
        """Send a local file/document via Telegram."""
        token = self._get_token()
        target_chat = chat_id.strip() or self._get_default_chat_id()
        if not token:
            return {"success": False, "error": "Telegram bot_token not configured"}
        if not target_chat:
            return {"success": False, "error": "chat_id is required"}

        fp = Path(file_path).expanduser().resolve()
        if not fp.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            url = f"{self.API_BASE}/bot{token}/sendDocument"
            async with httpx.AsyncClient(timeout=45.0) as client:
                with open(fp, "rb") as f:
                    files = {"document": (fp.name, f)}
                    data = {"chat_id": target_chat}
                    if caption:
                        data["caption"] = caption
                    resp = await client.post(url, data=data, files=files)
                    if resp.status_code == 200:
                        return {"success": True, "result": resp.json().get("result")}
                    return {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def read_messages(self, limit: int = 5) -> dict:
        """Read recent messages sent to the bot."""
        token = self._get_token()
        if not token:
            return {"success": False, "error": "Telegram bot_token not configured"}
        try:
            url = f"{self.API_BASE}/bot{token}/getUpdates"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params={"limit": limit, "allowed_updates": ["message"]})
                if resp.status_code == 200:
                    updates = resp.json().get("result", [])
                    messages = []
                    for u in updates:
                        m = u.get("message", {})
                        if m:
                            messages.append({
                                "message_id": m.get("message_id"),
                                "from": m.get("from", {}).get("username") or m.get("from", {}).get("first_name"),
                                "chat_id": m.get("chat", {}).get("id"),
                                "text": m.get("text", ""),
                                "date": m.get("date"),
                            })
                    return {"success": True, "messages": messages}
                return {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "telegram_send",
                "description": "Send a message or notification via Telegram to a user or group chat",
                "parameters": {
                    "text": {"type": "string", "description": "Message text to send"},
                    "chat_id": {"type": "string", "description": "Target Telegram chat ID (or leave blank to use default)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "telegram_send_file",
                "description": "Send a local file, document, or image to a Telegram chat",
                "parameters": {
                    "file_path": {"type": "string", "description": "Path to local file to upload and send"},
                    "chat_id": {"type": "string", "description": "Target Telegram chat ID (or leave blank to use default)"},
                    "caption": {"type": "string", "description": "Optional caption for the file"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "telegram_read",
                "description": "Read recent incoming messages from Telegram",
                "parameters": {
                    "limit": {"type": "integer", "description": "Number of recent messages to read (default 5)"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]


# ─── Convenience: all built-in integrations ──────────────────
