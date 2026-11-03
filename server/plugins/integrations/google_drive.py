"""
Google Drive Integration Plugin
Full Google Drive v3 API implementation with Unified Google OAuth2.
"""

from __future__ import annotations

import io
import json
import asyncio
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration
from .google_oauth import build_google_credentials_object, run_unified_google_oauth, UNIFIED_GOOGLE_SCOPES


class GoogleDriveIntegration(BaseIntegration):
    """Google Drive integration — search, read, upload, and organize files."""
    
    INTEGRATION_ID = "google_drive"
    DISPLAY_NAME = "Google Drive"
    DESCRIPTION = "Search, read, and upload files in Google Drive"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.FILE_READ, Permission.FILE_WRITE]
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def _get_drive_service(self):
        from googleapiclient.discovery import build
        creds = build_google_credentials_object(self.credentials, scopes=UNIFIED_GOOGLE_SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    
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
        if not self.credentials or not self.credentials.access_token:
            return False
        try:
            loop = asyncio.get_running_loop()
            def _test():
                service = self._get_drive_service()
                service.about().get(fields="user(emailAddress)").execute()
                return True
            return await loop.run_in_executor(None, _test)
        except Exception as e:
            logger.error(f"Google Drive test_connection failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        files = await self.list_files(query="", count=20)
        self.last_sync = datetime.now()
        return {
            "files_synced": len(files),
            "sample": files[:5],
            "synced_at": datetime.now().isoformat(),
        }

    async def list_files(self, query: str = "", count: int = 10) -> list[dict[str, Any]]:
        if not self.credentials:
            return []
        loop = asyncio.get_running_loop()
        def _list():
            service = self._get_drive_service()
            q = "trashed=false"
            if query:
                safe_query = query.replace("'", "\'")
                q = f"{q} and name contains '{safe_query}'"
            response = service.files().list(
                q=q,
                pageSize=max(1, min(int(count), 50)),
                fields="files(id,name,mimeType,modifiedTime,size,webViewLink)",
            ).execute()
            return response.get("files", [])
        return await loop.run_in_executor(None, _list)

    async def read_file_text(self, file_id: str) -> dict[str, Any]:
        if not self.credentials:
            return {"error": "Not authenticated"}
        if not file_id:
            return {"error": "file_id is required"}
        loop = asyncio.get_running_loop()
        def _read():
            from googleapiclient.http import MediaIoBaseDownload
            service = self._get_drive_service()
            meta = service.files().get(fileId=file_id, fields="id,name,mimeType,webViewLink").execute()
            mime = meta.get("mimeType", "")

            buffer = io.BytesIO()
            if mime == "application/vnd.google-apps.document":
                request = service.files().export_media(fileId=file_id, mimeType="text/plain")
            elif mime == "application/vnd.google-apps.spreadsheet":
                request = service.files().export_media(fileId=file_id, mimeType="text/csv")
            elif mime == "application/vnd.google-apps.presentation":
                request = service.files().export_media(fileId=file_id, mimeType="text/plain")
            else:
                request = service.files().get_media(fileId=file_id)

            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            content_bytes = buffer.getvalue()
            content = content_bytes.decode("utf-8", errors="replace")
            return {
                "id": meta.get("id", file_id),
                "name": meta.get("name", ""),
                "mimeType": mime,
                "webViewLink": meta.get("webViewLink", ""),
                "content_preview": content[:6000],
                "bytes": len(content_bytes),
            }
        return await loop.run_in_executor(None, _read)

    async def upload_file(self, file_path: str, folder_id: str = "", title: str = "") -> dict[str, Any]:
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}
        fp = Path(file_path).expanduser().resolve()
        if not fp.exists() or not fp.is_file():
            return {"success": False, "error": f"Local file not found: {file_path}"}
        loop = asyncio.get_running_loop()
        def _upload():
            from googleapiclient.http import MediaFileUpload
            service = self._get_drive_service()
            mime_type, _ = mimetypes.guess_type(str(fp))
            media = MediaFileUpload(str(fp), mimetype=mime_type or "application/octet-stream", resumable=True)
            metadata: dict[str, Any] = {"name": title.strip() or fp.name}
            if folder_id.strip():
                metadata["parents"] = [folder_id.strip()]
            uploaded = service.files().create(body=metadata, media_body=media, fields="id,name,webViewLink").execute()
            return {
                "success": True,
                "id": uploaded.get("id"),
                "name": uploaded.get("name"),
                "webViewLink": uploaded.get("webViewLink"),
            }
        return await loop.run_in_executor(None, _upload)
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "google_drive_search",
                "description": "Search for files and documents in Google Drive",
                "parameters": {
                    "query": {"type": "string", "description": "Search query (filename keyword)"},
                    "count": {"type": "integer", "description": "Max results (default 10)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_drive_read",
                "description": "Read text/CSV content from a Google Drive file, Google Doc, or Google Sheet by file_id",
                "parameters": {"file_id": {"type": "string", "description": "Drive file ID"}},
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_drive_upload",
                "description": "Upload a local file to Google Drive",
                "parameters": {
                    "file_path": {"type": "string", "description": "Local file path to upload"},
                    "title": {"type": "string", "description": "Optional target filename in Drive"},
                    "folder_id": {"type": "string", "description": "Optional parent Drive folder ID"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]
