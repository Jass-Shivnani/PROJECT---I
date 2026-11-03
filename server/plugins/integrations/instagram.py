"""
Instagram Graph Integration Plugin
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from loguru import logger
import httpx

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration


class InstagramIntegration(BaseIntegration):
    """Instagram — read profile, media posts, and insights via Instagram Graph API."""
    
    INTEGRATION_ID = "instagram"
    DISPLAY_NAME = "Instagram"
    DESCRIPTION = "Read Instagram profile, posts, and messages"
    AUTH_TYPE = AuthType.TOKEN
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = ["instagram_basic", "instagram_manage_messages", "pages_messaging"]
    
    GRAPH_API = "https://graph.instagram.com/v21.0"
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        token = str(params.get("access_token") or params.get("token") or "").strip()
        if not token and self.credentials:
            token = self.credentials.access_token or ""
        if not token:
            return False
        self.credentials = IntegrationCredentials(
            integration_id=self.INTEGRATION_ID,
            auth_type=AuthType.TOKEN,
            access_token=token,
        )
        return True
    
    async def test_connection(self) -> bool:
        if not self.credentials or not self.credentials.access_token:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.GRAPH_API}/me",
                    params={"fields": "id,username", "access_token": self.credentials.access_token},
                )
                return r.status_code == 200 and "id" in r.json()
        except Exception as e:
            logger.error(f"Instagram test failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        if not self.credentials:
            return {"error": "Not authenticated"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.GRAPH_API}/me",
                    params={"fields": "id,username,media_count,account_type", "access_token": self.credentials.access_token},
                )
                data = r.json()
                self.last_sync = datetime.now()
                return {
                    "id": data.get("id", ""),
                    "username": data.get("username", ""),
                    "media_count": data.get("media_count", 0),
                    "account_type": data.get("account_type", ""),
                }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_recent_posts(self, count: int = 5) -> list[dict]:
        if not self.credentials:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.GRAPH_API}/me/media",
                    params={
                        "fields": "id,caption,media_type,timestamp,permalink",
                        "limit": count,
                        "access_token": self.credentials.access_token,
                    },
                )
                return r.json().get("data", [])
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "instagram_profile",
                "description": "Get Instagram account profile info and media count",
                "parameters": {},
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "instagram_posts",
                "description": "Get recent Instagram media posts and captions",
                "parameters": {
                    "count": {"type": "integer", "description": "Number of posts (default 5)"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]
