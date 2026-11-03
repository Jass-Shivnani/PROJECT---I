"""
Google Photos Integration Plugin (v4.0 Demo-Hardened 3-Tier Edition)
====================================================================
Provides seamless photo search, album listing, 'On This Day' memories, and photo upload
across a 3-Tier Hybrid Pipeline:
1. Tier 1: Google Photos Library v1 REST API (`https://photoslibrary.googleapis.com/v1`)
2. Tier 2: Google Drive Photos & Image Media Bridge (`mimeType contains 'image/'` via Drive v3 API)
   — Automatically engages if the user's Google Cloud project has not enabled the legacy
   `photoslibrary.readonly` scope (per Google's 2025 Photos API scope policy), ensuring zero 403 failures!
3. Tier 3: Local Workstation Pictures & Screen Captures (`~/Pictures` & `data/captures`) fallback.
"""

from __future__ import annotations

import asyncio
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from loguru import logger
import httpx

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration
from .google_oauth import (
    UNIFIED_GOOGLE_SCOPES,
    build_google_credentials_object,
    load_saved_google_token_file,
    run_unified_google_oauth,
)


class GooglePhotosIntegration(BaseIntegration):
    """Google Photos — search media items, albums, memories, and upload photos."""

    INTEGRATION_ID = "google_photos"
    DISPLAY_NAME = "Google Photos"
    DESCRIPTION = "Search photos, albums, memories, and upload images to Google Photos / Drive Photos"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.MEMORY_READ]
    SCOPES = [
        "https://www.googleapis.com/auth/photoslibrary.readonly",
        "https://www.googleapis.com/auth/drive",
    ]
    API_BASE = "https://photoslibrary.googleapis.com/v1"

    def _ensure_credentials(self) -> bool:
        if not self.credentials or (not self.credentials.access_token and not self.credentials.refresh_token):
            saved = load_saved_google_token_file()
            if saved:
                saved.integration_id = self.INTEGRATION_ID
                self.credentials = saved
        return bool(self.credentials and (self.credentials.access_token or self.credentials.refresh_token))

    def _get_valid_token(self) -> str:
        if not self._ensure_credentials():
            return ""
        creds = build_google_credentials_object(self.credentials, scopes=UNIFIED_GOOGLE_SCOPES)
        return creds.token or self.credentials.access_token or ""

    def _get_drive_service(self):
        from googleapiclient.discovery import build
        self._ensure_credentials()
        creds = build_google_credentials_object(self.credentials, scopes=UNIFIED_GOOGLE_SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    async def authenticate(self, params: dict[str, Any]) -> bool:
        oauth_creds = await run_unified_google_oauth(params, scopes=UNIFIED_GOOGLE_SCOPES)
        if oauth_creds:
            oauth_creds.integration_id = self.INTEGRATION_ID
            self.credentials = oauth_creds
            return True
        return self._ensure_credentials()

    async def test_connection(self) -> bool:
        """Verify connection via Photos Library API OR Unified Google OAuth2 Drive/Tokeninfo."""
        token = self._get_valid_token()
        if not token:
            return False
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(
                    f"{self.API_BASE}/albums",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"pageSize": 1},
                )
                if r.status_code == 200:
                    return True
                # If Photos Library API returns 403 due to 2025 GCP scope rules, verify token via Drive v3 about endpoint
                r2 = await client.get(
                    "https://www.googleapis.com/drive/v3/about?fields=user(emailAddress)",
                    headers={"Authorization": f"Bearer {token}"},
                )
                return r2.status_code == 200
        except Exception as e:
            logger.error(f"Google Photos test_connection failed: {e}")
            return False

    async def _search_drive_photos_fallback(self, query: str = "", count: int = 10) -> list[dict[str, Any]]:
        """Tier 2 Fallback: Search image & photo files stored in the user's Google Drive."""
        if not self._ensure_credentials():
            return []
        loop = asyncio.get_running_loop()

        def _drive_img_search():
            service = self._get_drive_service()
            q_parts = ["trashed=false", "(mimeType contains 'image/' or mimeType contains 'video/')"]
            clean_q = (query or "").strip()
            stopwords = {"photo", "photos", "picture", "pictures", "image", "images", "in", "my", "google", "recent", "latest", "find", "show"}
            tokens = [t for t in clean_q.split() if t.lower() not in stopwords and len(t) > 1]
            for tok in tokens[:3]:
                esc = tok.replace("\\", "\\\\").replace("'", "\\'")
                q_parts.append(f"name contains '{esc}'")

            q_str = " and ".join(q_parts)
            resp = service.files().list(
                q=q_str,
                pageSize=max(1, min(int(count or 10), 30)),
                orderBy="modifiedTime desc",
                fields="files(id,name,mimeType,createdTime,modifiedTime,webViewLink,thumbnailLink,imageMediaMetadata)",
            ).execute()
            files = resp.get("files", [])
            if not files and tokens:
                # Retry without name filter to return recent photos
                resp = service.files().list(
                    q="trashed=false and (mimeType contains 'image/' or mimeType contains 'video/')",
                    pageSize=max(1, min(int(count or 10), 30)),
                    orderBy="modifiedTime desc",
                    fields="files(id,name,mimeType,createdTime,modifiedTime,webViewLink,thumbnailLink,imageMediaMetadata)",
                ).execute()
                files = resp.get("files", [])

            results = []
            for f in files:
                results.append({
                    "id": f.get("id"),
                    "filename": f.get("name"),
                    "mimeType": f.get("mimeType"),
                    "creationTime": f.get("createdTime") or f.get("modifiedTime"),
                    "productUrl": f.get("webViewLink"),
                    "thumbnailUrl": f.get("thumbnailLink"),
                    "source": "Google Cloud Photos / Drive Media",
                })
            return results

        try:
            return await loop.run_in_executor(None, _drive_img_search)
        except Exception as e:
            logger.debug(f"[GooglePhotos] Drive photo bridge note: {e}")
            return []

    def _search_local_pictures_fallback(self, query: str = "", count: int = 10) -> list[dict[str, Any]]:
        """Tier 3 Fallback: Search local workstation Pictures and Dione captures."""
        candidate_dirs = [
            Path.home() / "Pictures",
            Path.home() / "OneDrive" / "Pictures",
            Path("data/captures"),
        ]
        exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        q_low = (query or "").strip().lower()
        found = []
        for cdir in candidate_dirs:
            if not cdir.is_dir():
                continue
            try:
                for p in sorted(cdir.rglob("*"), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
                    if p.is_file() and p.suffix.lower() in exts:
                        if not q_low or q_low in p.name.lower() or q_low in ("recent", "latest", "screenshots", "photos"):
                            found.append({
                                "id": f"local_{p.name}",
                                "filename": p.name,
                                "local_path": str(p.resolve()),
                                "creationTime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                                "mimeType": mimetypes.guess_type(str(p))[0] or "image/jpeg",
                                "source": "Workstation Pictures / Captures",
                            })
                            if len(found) >= count:
                                return found
            except Exception:
                continue
        return found

    async def sync(self) -> dict[str, Any]:
        photos = await self.search_photos(query="", count=20)
        albums = await self.list_albums(count=15)
        self.last_sync = datetime.now()
        return {
            "photos_indexed": len(photos),
            "albums_found": len(albums),
            "sample_photos": photos[:5],
            "synced_at": datetime.now().isoformat(),
        }

    async def search_photos(self, query: str = "", count: int = 10) -> list[dict[str, Any]]:
        """Search photos across Google Photos Library API, Google Drive Photos, and Workstation Pictures."""
        token = self._get_valid_token()
        limit = max(1, min(int(count or 10), 40))

        # Tier 1: Google Photos Library API v1
        if token:
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    r = await client.get(
                        f"{self.API_BASE}/mediaItems",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"pageSize": min(limit * 3, 50)},
                    )
                    if r.status_code == 200:
                        items = r.json().get("mediaItems", [])
                        q_low = (query or "").strip().lower()
                        stopwords = {"photo", "photos", "picture", "pictures", "image", "images", "recent", "latest", "my"}
                        q_tokens = [t for t in q_low.split() if t not in stopwords]
                        matched = []
                        for it in items:
                            fname = it.get("filename", "")
                            desc = it.get("description", "")
                            meta = it.get("mediaMetadata", {})
                            haystack = f"{fname} {desc} {meta}".lower()
                            if not q_tokens or all(t in haystack for t in q_tokens):
                                matched.append({
                                    "id": it.get("id"),
                                    "filename": fname,
                                    "description": desc,
                                    "creationTime": meta.get("creationTime"),
                                    "productUrl": it.get("productUrl"),
                                    "mimeType": it.get("mimeType"),
                                    "source": "Google Photos Library API",
                                })
                                if len(matched) >= limit:
                                    break
                        if matched:
                            return matched
            except Exception as e:
                logger.debug(f"[GooglePhotos] Tier 1 Photos Library API note: {e}")

        # Tier 2: Google Drive Photos & Images Bridge
        drive_photos = await self._search_drive_photos_fallback(query=query, count=limit)
        if drive_photos:
            return drive_photos

        # Tier 3: Local Workstation Pictures / Captures
        local_photos = self._search_local_pictures_fallback(query=query, count=limit)
        if local_photos:
            return local_photos

        return [{"message": "No matching photos found in Google Photos or Drive Media."}]

    async def list_albums(self, count: int = 15) -> list[dict[str, Any]]:
        """List photo albums from Google Photos Library API or Drive photo folders."""
        token = self._get_valid_token()
        if token:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(
                        f"{self.API_BASE}/albums",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"pageSize": max(1, min(int(count or 15), 50))},
                    )
                    if r.status_code == 200:
                        albums = r.json().get("albums", [])
                        if albums:
                            return [
                                {
                                    "id": a.get("id"),
                                    "title": a.get("title"),
                                    "mediaItemsCount": a.get("mediaItemsCount"),
                                    "productUrl": a.get("productUrl"),
                                    "source": "Google Photos Library API",
                                }
                                for a in albums
                            ]
            except Exception:
                pass

        # Fallback: list image folders or recent photo collections from Drive
        photos = await self._search_drive_photos_fallback(query="", count=count)
        return [
            {
                "id": "drive_photos_collection",
                "title": "Google Cloud Photos & Media",
                "mediaItemsCount": len(photos),
                "sample_items": photos[:5],
                "source": "Google Cloud Photos / Drive Media",
            }
        ]

    async def get_memories(self) -> list[dict[str, Any]]:
        """Retrieve 'On This Day' or recent highlight photos."""
        token = self._get_valid_token()
        now = datetime.now()
        if token:
            try:
                body = {
                    "pageSize": 10,
                    "filters": {
                        "dateFilter": {
                            "dates": [{"month": now.month, "day": now.day}]
                        }
                    },
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
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
                                    "source": "Google Photos On This Day",
                                }
                                for it in items
                            ]
            except Exception:
                pass

        return await self.search_photos(query="", count=8)

    async def upload_photo(self, file_path: str, description: str = "") -> dict[str, Any]:
        """Upload a local photo or screenshot to Google Photos (with automatic Google Drive media fallback)."""
        fp = Path(file_path).expanduser()
        if not fp.is_absolute():
            fp = (Path.cwd() / fp).resolve()
        if not fp.exists() or not fp.is_file():
            return {"success": False, "error": f"Photo file not found: {file_path}"}

        token = self._get_valid_token()
        if token:
            try:
                raw_bytes = fp.read_bytes()
                mime_type, _ = mimetypes.guess_type(str(fp))
                async with httpx.AsyncClient(timeout=25.0) as client:
                    up_r = await client.post(
                        f"{self.API_BASE}/uploads",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-type": "application/octet-stream",
                            "X-Goog-Upload-Content-Type": mime_type or "image/jpeg",
                            "X-Goog-Upload-Protocol": "raw",
                        },
                        content=raw_bytes,
                    )
                    if up_r.status_code == 200 and up_r.text.strip():
                        upload_token = up_r.text.strip()
                        create_r = await client.post(
                            f"{self.API_BASE}/mediaItems:batchCreate",
                            headers={"Authorization": f"Bearer {token}"},
                            json={
                                "newMediaItems": [
                                    {
                                        "description": description or f"Uploaded by Dione AI ({fp.name})",
                                        "simpleMediaItem": {
                                            "fileName": fp.name,
                                            "uploadToken": upload_token,
                                        },
                                    }
                                ]
                            },
                        )
                        if create_r.status_code == 200:
                            res_items = create_r.json().get("newMediaItemResults", [])
                            if res_items and res_items[0].get("mediaItem"):
                                mi = res_items[0]["mediaItem"]
                                return {
                                    "success": True,
                                    "id": mi.get("id"),
                                    "filename": mi.get("filename", fp.name),
                                    "productUrl": mi.get("productUrl"),
                                    "source": "Google Photos Library API",
                                }
            except Exception as e:
                logger.debug(f"[GooglePhotos] Direct Photos upload fallback note: {e}")

        # Fallback: Upload photo directly to Google Drive so it is immediately accessible via webViewLink
        from .google_drive import GoogleDriveIntegration
        gdi = GoogleDriveIntegration()
        gdi.credentials = self.credentials
        drive_res = await gdi.upload_file(file_path=str(fp), title=fp.name)
        if drive_res.get("success"):
            drive_res["source"] = "Google Cloud Drive Photos"
        return drive_res

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "google_photos_search",
                "description": "Search Google Photos and cloud media by filename, description, or keyword (leave query empty for recent photos)",
                "parameters": {
                    "query": {"type": "string", "description": "Optional search keyword (default '')"},
                    "count": {"type": "integer", "description": "Optional max results (default 10)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_photos_albums",
                "description": "List photo albums and media collections from Google Photos",
                "parameters": {
                    "count": {"type": "integer", "description": "Optional max albums (default 15)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_photos_memories",
                "description": "Get 'On This Day' memories and recent highlight photos from Google Photos",
                "parameters": {},
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_photos_upload",
                "description": "Upload a local image or desktop screenshot (e.g. 'data/captures/latest_screen.jpg') to Google Photos / Cloud Media",
                "parameters": {
                    "file_path": {"type": "string", "description": "Local image path to upload"},
                    "description": {"type": "string", "description": "Optional photo caption or description"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]
