"""
Google Drive Integration Plugin
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


class GoogleDriveIntegration(BaseIntegration):
    """Google Drive integration — file access and management."""
    
    INTEGRATION_ID = "google_drive"
    DISPLAY_NAME = "Google Drive"
    DESCRIPTION = "Access and manage files in Google Drive"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.FILE_READ, Permission.FILE_WRITE]
    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ]
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        access_token = params.get("access_token", "")
        if access_token:
            self.credentials = IntegrationCredentials(
                integration_id=self.INTEGRATION_ID,
                auth_type=AuthType.OAUTH2,
                access_token=access_token,
                refresh_token=params.get("refresh_token", ""),
                token_expiry=datetime.now() + timedelta(hours=1),
                extra={
                    "client_id": params.get("client_id", ""),
                    "client_secret": params.get("client_secret", ""),
                    "token_uri": params.get("token_uri", "https://oauth2.googleapis.com/token"),
                },
            )
            return True

        client_secret_path = params.get("client_secret_path", "")
        if client_secret_path:
            try:
                from google_auth_oauthlib.flow import InstalledAppFlow

                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, self.SCOPES)
                creds = flow.run_local_server(port=0)

                self.credentials = IntegrationCredentials(
                    integration_id=self.INTEGRATION_ID,
                    auth_type=AuthType.OAUTH2,
                    access_token=creds.token or "",
                    refresh_token=creds.refresh_token or "",
                    token_expiry=creds.expiry,
                    extra={
                        "client_secret_path": client_secret_path,
                        "client_id": creds.client_id or "",
                        "client_secret": getattr(creds, "client_secret", "") or "",
                        "token_uri": creds.token_uri or "https://oauth2.googleapis.com/token",
                    },
                )
                return True
            except Exception as e:
                logger.error(f"Google Drive OAuth authentication failed: {e}")
                return False

        return False
    
    async def test_connection(self) -> bool:
        if not self.credentials:
            return False
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            creds = Credentials(
                token=self.credentials.access_token,
                refresh_token=self.credentials.refresh_token,
                token_uri=self.credentials.extra.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=self.credentials.extra.get("client_id", ""),
                client_secret=self.credentials.extra.get("client_secret", ""),
                scopes=self.SCOPES,
            )

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self.credentials.access_token = creds.token or self.credentials.access_token
                self.credentials.token_expiry = creds.expiry

            service = build("drive", "v3", credentials=creds, cache_discovery=False)
            service.about().get(fields="user(emailAddress)").execute()
            return True
        except Exception as e:
            logger.error(f"Google Drive test_connection failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        files = await self.list_files(query="", count=20)
        return {
            "files_synced": len(files),
            "sample": files[:5],
            "synced_at": datetime.now().isoformat(),
        }

    async def list_files(self, query: str = "", count: int = 10) -> list[dict[str, Any]]:
        if not self.credentials:
            return []

        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials(
            token=self.credentials.access_token,
            refresh_token=self.credentials.refresh_token,
            token_uri=self.credentials.extra.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=self.credentials.extra.get("client_id", ""),
            client_secret=self.credentials.extra.get("client_secret", ""),
            scopes=self.SCOPES,
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.credentials.access_token = creds.token or self.credentials.access_token
            self.credentials.token_expiry = creds.expiry

        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        q = "trashed=false"
        if query:
            safe_query = query.replace("'", "\\'")
            q = f"{q} and name contains '{safe_query}'"

        response = service.files().list(
            q=q,
            pageSize=max(1, min(int(count), 50)),
            fields="files(id,name,mimeType,modifiedTime,size,webViewLink)",
        ).execute()
        return response.get("files", [])

    async def read_file_text(self, file_id: str) -> dict[str, Any]:
        if not self.credentials:
            return {"error": "Not authenticated"}
        if not file_id:
            return {"error": "file_id is required"}

        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        creds = Credentials(
            token=self.credentials.access_token,
            refresh_token=self.credentials.refresh_token,
            token_uri=self.credentials.extra.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=self.credentials.extra.get("client_id", ""),
            client_secret=self.credentials.extra.get("client_secret", ""),
            scopes=self.SCOPES,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.credentials.access_token = creds.token or self.credentials.access_token
            self.credentials.token_expiry = creds.expiry

        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        meta = service.files().get(fileId=file_id, fields="id,name,mimeType").execute()
        mime = meta.get("mimeType", "")

        buffer = io.BytesIO()
        if mime == "application/vnd.google-apps.document":
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
            "content_preview": content[:4000],
            "bytes": len(content_bytes),
        }
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "google_drive_search",
                "description": "Search for files in Google Drive",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "count": {"type": "integer", "description": "Max results (default 10)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_drive_read",
                "description": "Read a file from Google Drive",
                "parameters": {"file_id": {"type": "string", "description": "Drive file ID"}},
                "integration": self.INTEGRATION_ID,
            },
        ]
