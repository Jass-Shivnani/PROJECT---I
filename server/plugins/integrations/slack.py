"""
Slack Workspace Integration Plugin
"""

from __future__ import annotations

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger
import httpx

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration


class SlackIntegration(BaseIntegration):
    """
    Slack — list channels, read messages, and send messages via Webhook or Bot Token.
    Automatically resolves #channel-name to Slack channel IDs.
    """
    
    INTEGRATION_ID = "slack"
    DISPLAY_NAME = "Slack"
    DESCRIPTION = "Send and read Slack messages across workspace channels"
    AUTH_TYPE = AuthType.TOKEN
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = ["channels:read", "chat:write", "channels:history"]

    def __init__(self):
        super().__init__()
        self._webhook_url: Optional[str] = None
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        webhook_url = str(params.get("webhook_url", "")).strip()
        bot_token = str(params.get("bot_token") or params.get("token") or params.get("access_token") or "").strip()
        
        if webhook_url:
            self._webhook_url = webhook_url
            self.credentials = IntegrationCredentials(
                integration_id=self.INTEGRATION_ID,
                auth_type=AuthType.TOKEN,
                access_token="webhook",
                extra={"webhook_url": webhook_url},
            )
            return True
        elif bot_token:
            self.credentials = IntegrationCredentials(
                integration_id=self.INTEGRATION_ID,
                auth_type=AuthType.TOKEN,
                access_token=bot_token,
            )
            return True
        if self.credentials and (self.credentials.access_token or self.credentials.extra.get("webhook_url")):
            return True
        return False
    
    async def test_connection(self) -> bool:
        if not self.credentials:
            return False
        if self._webhook_url or self.credentials.extra.get("webhook_url"):
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {self.credentials.access_token}"},
                )
                return bool(r.json().get("ok", False))
        except Exception as e:
            logger.error(f"Slack test failed: {e}")
            return False
    
    async def list_channels(self) -> list[dict[str, Any]]:
        if not self.credentials or self.credentials.access_token == "webhook":
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://slack.com/api/conversations.list",
                    headers={"Authorization": f"Bearer {self.credentials.access_token}"},
                    params={"types": "public_channel,private_channel", "limit": 100},
                )
                data = r.json()
                if data.get("ok"):
                    return [
                        {"id": c.get("id"), "name": c.get("name"), "is_private": c.get("is_private", False)}
                        for c in data.get("channels", [])
                    ]
        except Exception as e:
            logger.error(f"Slack list_channels failed: {e}")
        return []

    async def _resolve_channel_id(self, channel: str) -> str:
        clean = channel.strip().lstrip("#")
        if not clean or (clean.startswith(("C", "G", "D")) and clean[1:].isalnum()):
            return clean
        channels = await self.list_channels()
        for c in channels:
            if c.get("name", "").lower() == clean.lower():
                return c["id"]
        return clean

    async def sync(self) -> dict[str, Any]:
        channels = await self.list_channels()
        self.last_sync = datetime.now()
        return {
            "channels_accessible": len(channels),
            "channels": channels[:10],
            "synced_at": datetime.now().isoformat(),
        }
    
    async def send_message(self, channel: str = "", text: str = "") -> dict:
        """Send a message to Slack."""
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}
        try:
            if self._webhook_url or self.credentials.extra.get("webhook_url"):
                url = self._webhook_url or self.credentials.extra["webhook_url"]
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.post(url, json={"text": text})
                    return {"success": r.status_code == 200}
            else:
                target_channel = await self._resolve_channel_id(channel)
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={"Authorization": f"Bearer {self.credentials.access_token}"},
                        json={"channel": target_channel, "text": text},
                    )
                    data = r.json()
                    return {"success": data.get("ok", False), "channel": target_channel, "ts": data.get("ts"), "error": data.get("error")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def read_messages(self, channel: str, count: int = 10) -> list[dict]:
        """Read recent messages from a Slack channel."""
        if not self.credentials or not self.credentials.access_token or self.credentials.access_token == "webhook":
            return [{"error": "Bot token required for reading messages"}]
        try:
            target_channel = await self._resolve_channel_id(channel)
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://slack.com/api/conversations.history",
                    headers={"Authorization": f"Bearer {self.credentials.access_token}"},
                    params={"channel": target_channel, "limit": count},
                )
                data = r.json()
                if data.get("ok"):
                    return [
                        {"user": m.get("user", ""), "text": m.get("text", ""), "ts": m.get("ts", "")}
                        for m in data.get("messages", [])
                    ]
                return [{"error": data.get("error", "Unknown error")}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "slack_send",
                "description": "Send a message to a Slack channel (supports #channel-name or channel ID) or webhook",
                "parameters": {
                    "text": {"type": "string", "description": "Message text"},
                    "channel": {"type": "string", "description": "Channel name (e.g. #general) or ID"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "slack_read",
                "description": "Read recent messages from a Slack channel",
                "parameters": {
                    "channel": {"type": "string", "description": "Channel name (e.g. #general) or ID"},
                    "count": {"type": "integer", "description": "Number of messages (default 10)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "slack_channels",
                "description": "List accessible Slack channels in the workspace",
                "parameters": {},
                "integration": self.INTEGRATION_ID,
            },
        ]
