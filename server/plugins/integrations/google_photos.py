"""
Google Photos Integration Plugin
Real Google Photos Library v1 REST API implementation with Unified Google OAuth2.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from loguru import logger
import httpx

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration
from .google_oauth import build_google_credentials_object, run_unified_google_oauth, UNIFIED_GOOGLE_SCOPES


class GooglePhotosIntegration(BaseIntegration):
    """Google Photos — search media items, albums, and On This Day memories."""
    
    INTEGRATION_ID = "google_photos"
    DISPLAY_NAME = "Google Photos"
    DESCRIPTION = "Access photos, albums, and memories from Google Photos"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.MEMORY_READ]
    SCOPES = [
        "https://www.googleapis.com/auth/photoslibrary.readonly",
    ]
    API_BASE = "https://photoslibrary.googleapis.com/v1"

    def _get_valid_token(self) -> str:
        if not self.credentials:
            return ""
        creds = build_google_credentials_object(self.credentials, scopes=UNIFIED_GOOGLE_SCOPES)
        return creds.token or self.credentials.access_token or ""
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        oauth_creds = await run_unified_google_oauth(params, scopes=UNIFIED_GOOGLE_SCOPES)
        if oauth_creds:
            oauth_creds.integration_id = self.INTEGRATION_ID
            self.credentials = oauth_creds
            return True
        if self.credentials and self.credentials.access_token:
            return True
        return False
    
    async def test_connection(self) -> bool:
        token = self._get_valid_token()
        if not token:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.API_BASE}/albums",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"pageSize": 1},
                )
                return r.status_code == 200
        except Exception as e:
            logger.error(f"Google Photos test_connection failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        token = self._get_valid_token()
        if not token:
            return {"error": "Not authenticated"}
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                albums_r = await client.get(
                    f"{self.API_BASE}/albums",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"pageSize": 20},
                )
                media_r = await client.get(
                    f"{self.API_BASE}/mediaItems",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"pageSize": 25},
                )
                albums = albums_r.json().get("albums", []) if albums_r.status_code == 200 else []
                media = media_r.json().get("mediaItems", []) if media_r.status_code == 200 else []
                self.last_sync = datetime.now()
                return {
                    "photos_indexed": len(media),
                    "albums_found": len(albums),
                    "synced_at": datetime.now().isoformat(),
                }
        except Exception as e:
            return {"error": str(e)}

    async def search_photos(self, query: str = "", count: int = 10) -> list[dict[str, Any]]:
        token = self._get_valid_token()
        if not token:
            return []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"{self.API_BASE}/mediaItems",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"pageSize": max(1, min(int(count) * 3, 50))},
                )
                if r.status_code != 200:
                    return [{"error": r.text}]
                items = r.json().get("mediaItems", [])
                q_low = query.strip().lower()
                matched = []
                for it in items:
                    fname = it.get("filename", "")
                    desc = it.get("description", "")
                    meta = it.get("mediaMetadata", {})
                    if not q_low or q_low in fname.lower() or q_low in desc.lower() or q_low in str(meta).lower():
                        matched.append({
                            "id": it.get("id"),
                            "filename": fname,
                            "description": desc,
                            "creationTime": meta.get("creationTime"),
                            "productUrl": it.get("productUrl"),
                            "mimeType": it.get("mimeType"),
                        })
                        if len(matched) >= count:
                            break
                return matched
        except Exception as e:
            return [{"error": str(e)}]

    async def get_memories(self) -> list[dict[str, Any]]:
        """Retrieve 'On This Day' or recent highlight photos."""
        token = self._get_valid_token()
        if not token:
            return []
        now = datetime.now()
        try:
            body = {
                "pageSize": 10,
                "filters": {
                    "dateFilter": {
                        "dates": [{"month": now.month, "day": now.day}]
                    }
                },
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.API_BASE}/mediaItems:search",
                    headers={"Authorization": f"Bearer {token}"},
                    json=body,
                )
                if r.status_code == 200:
                    items = r.json().get("mediaItems", [])
                    if items:
                        return [
                            {
                                "id": it.get("id"),
                                "filename": it.get("filename"),
                                "creationTime": it.get("mediaMetadata", {}).get("creationTime"),
                                "productUrl": it.get("productUrl"),
                            }
                            for it in items
                        ]
            # Fallback to recent photos if none on exact day
            return await self.search_photos(query="", count=5)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "google_photos_search",
                "description": "Search Google Photos by filename, description, or metadata",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "count": {"type": "integer", "description": "Max results (default 10)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_photos_memories",
                "description": "Get 'On This Day' memories and recent highlights from Google Photos",
                "parameters": {},
                "integration": self.INTEGRATION_ID,
            },
        ]
