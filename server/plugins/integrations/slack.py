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
    Slack — read channels, send messages via webhook or Bot API.
    
    Can use either:
    1. Webhook URL (simple, send-only) — set webhook_url in params
    2. Bot Token (full API) — set bot_token in params
    """
    
    INTEGRATION_ID = "slack"
    DISPLAY_NAME = "Slack"
    DESCRIPTION = "Send and read Slack messages"
    AUTH_TYPE = AuthType.TOKEN
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = []

    def __init__(self):
        super().__init__()
        self._webhook_url: Optional[str] = None
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        webhook_url = params.get("webhook_url", "")
        bot_token = params.get("bot_token", "")
        
        if webhook_url:
            self._webhook_url = webhook_url
            self.credentials = IntegrationCredentials(
                auth_type=AuthType.TOKEN,
                access_token="webhook",
                extra={"webhook_url": webhook_url},
            )
            return True
        elif bot_token:
            self.credentials = IntegrationCredentials(
                auth_type=AuthType.TOKEN,
                access_token=bot_token,
            )
            return True
        return False
    
    async def test_connection(self) -> bool:
        if not self.credentials:
            return False
        
        if self._webhook_url:
            return True  # Webhooks don't have a test endpoint
        
        # Test bot token via auth.test
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {self.credentials.access_token}"},
                )
                data = r.json()
                return data.get("ok", False)
        except Exception as e:
            logger.error(f"Slack test failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        return {"channels_accessible": 0}
    
    async def send_message(self, channel: str = "", text: str = "") -> dict:
        """Send a message to Slack."""
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}
        
        try:
            import httpx
            
            if self._webhook_url or self.credentials.extra.get("webhook_url"):
                url = self._webhook_url or self.credentials.extra["webhook_url"]
                async with httpx.AsyncClient() as client:
                    r = await client.post(url, json={"text": text})
                    return {"success": r.status_code == 200}
            else:
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={"Authorization": f"Bearer {self.credentials.access_token}"},
                        json={"channel": channel, "text": text},
                    )
                    data = r.json()
                    return {"success": data.get("ok", False)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def read_messages(self, channel: str, count: int = 10) -> list[dict]:
        """Read recent messages from a Slack channel (requires bot token)."""
        if not self.credentials or not self.credentials.access_token:
            return [{"error": "Bot token required for reading messages"}]
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://slack.com/api/conversations.history",
                    headers={"Authorization": f"Bearer {self.credentials.access_token}"},
                    params={"channel": channel, "limit": count},
                )
                data = r.json()
                if data.get("ok"):
                    return [
                        {
                            "user": m.get("user", ""),
                            "text": m.get("text", ""),
                            "ts": m.get("ts", ""),
                        }
                        for m in data.get("messages", [])
                    ]
                return [{"error": data.get("error", "Unknown error")}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "slack_send",
                "description": "Send a message to a Slack channel or webhook",
                "parameters": {
                    "text": {"type": "string", "description": "Message text"},
                    "channel": {"type": "string", "description": "Channel ID (only for bot token)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "slack_read",
                "description": "Read recent messages from a Slack channel (requires bot token)",
                "parameters": {
                    "channel": {"type": "string", "description": "Channel ID"},
                    "count": {"type": "integer", "description": "Number of messages"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]


# ─── Instagram Integration ───────────────────────────────────
