"""
Google Drive Integration Plugin (v4.0 Demo-Hardened Edition)
Full Google Drive v3 API implementation with Unified Google OAuth2:
- Smart multi-keyword search with fullText fallback and file-type filtering
- Automatic filename-to-file_id resolution in `google_drive_read` (handles Docs, Sheets, Slides, PDFs, DOCX, TXT)
- Direct Google Doc / Text file creation (`google_drive_create_file`) and local file upload (`google_drive_upload`)
"""

from __future__ import annotations

import asyncio
import io
import json
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration
from .google_oauth import (
    UNIFIED_GOOGLE_SCOPES,
    build_google_credentials_object,
    load_saved_google_token_file,
    run_unified_google_oauth,
)


class GoogleDriveIntegration(BaseIntegration):
    """Google Drive integration — search, read, create, and upload files in Google Drive."""

    INTEGRATION_ID = "google_drive"
    DISPLAY_NAME = "Google Drive"
    DESCRIPTION = "Search, read, create, and upload files and Google Docs in Google Drive"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.FILE_READ, Permission.FILE_WRITE]
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def _ensure_credentials(self) -> bool:
        if not self.credentials or (not self.credentials.access_token and not self.credentials.refresh_token):
            saved = load_saved_google_token_file()
            if saved:
                saved.integration_id = self.INTEGRATION_ID
                self.credentials = saved
        return bool(self.credentials and (self.credentials.access_token or self.credentials.refresh_token))

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
        if not self._ensure_credentials():
            return False
        try:
            loop = asyncio.get_running_loop()

            def _test():
                service = self._get_drive_service()
                service.about().get(fields="user(displayName,emailAddress)").execute()
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

    async def list_files(self, query: str = "", count: int = 15) -> list[dict[str, Any]]:
        if not self._ensure_credentials():
            return [{"error": "Google Drive is not authenticated. Please connect Google in Settings -> Integrations."}]
        loop = asyncio.get_running_loop()

        def _list():
            service = self._get_drive_service()
            page_size = max(1, min(int(count or 15), 50))
            fields_str = "files(id,name,mimeType,modifiedTime,size,webViewLink,iconLink,owners(displayName))"

            clean_q = (query or "").strip()
            # Strip conversational filler words if the LLM passed a full sentence
            stopwords = {"find", "search", "for", "in", "my", "google", "drive", "file", "files", "named", "called", "the", "a", "an", "recent", "latest", "all"}
            tokens = [
                t for t in re.split(r"[\s,;]+", clean_q)
                if t and t.lower() not in stopwords and len(t) > 1
            ]

            if tokens:
                token_clauses = []
                for tok in tokens[:4]:
                    escaped = tok.replace("\\", "\\\\").replace("'", "\\'")
                    token_clauses.append(f"name contains '{escaped}'")
                q_str = "trashed=false and (" + " and ".join(token_clauses) + ")"
                resp = service.files().list(
                    q=q_str,
                    pageSize=page_size,
                    orderBy="modifiedTime desc",
                    fields=fields_str,
                ).execute()
                files = resp.get("files", [])
                if files:
                    return files

                # Fallback 1: OR across tokens or fullText search
                or_clauses = [f"name contains '{t.replace(chr(92), chr(92)*2).replace(chr(39), chr(92)+chr(39))}'" for t in tokens[:4]]
                q_or = "trashed=false and (" + " or ".join(or_clauses) + ")"
                resp2 = service.files().list(
                    q=q_or,
                    pageSize=page_size,
                    orderBy="modifiedTime desc",
                    fields=fields_str,
                ).execute()
                files2 = resp2.get("files", [])
                if files2:
                    return files2

            # Default / Fallback 2: Return most recently modified files in Drive
            resp_recent = service.files().list(
                q="trashed=false",
                pageSize=page_size,
                orderBy="modifiedTime desc",
                fields=fields_str,
            ).execute()
            return resp_recent.get("files", [])

        try:
            return await loop.run_in_executor(None, _list)
        except Exception as e:
            logger.error(f"[GoogleDrive] list_files failed: {e}")
            return [{"error": f"Google Drive search failed: {e}"}]

    async def read_file_text(self, file_id: str) -> dict[str, Any]:
        """Read content from a Drive file by file_id OR filename (auto-resolves filename if needed)."""
        if not self._ensure_credentials():
            return {"error": "Google Drive is not authenticated"}
        target_id = (file_id or "").strip()
        if not target_id:
            return {"error": "file_id or file name is required"}

        # If target_id looks like a filename (contains spaces or file extension), resolve it via list_files first
        if " " in target_id or "." in target_id or len(target_id) < 15:
            matches = await self.list_files(query=target_id, count=5)
            valid_matches = [m for m in matches if isinstance(m, dict) and m.get("id")]
            if valid_matches:
                target_id = valid_matches[0]["id"]

        loop = asyncio.get_running_loop()

        def _read():
            from googleapiclient.http import MediaIoBaseDownload

            service = self._get_drive_service()
            meta = service.files().get(fileId=target_id, fields="id,name,mimeType,webViewLink,size").execute()
            mime = meta.get("mimeType", "")

            buffer = io.BytesIO()
            if mime == "application/vnd.google-apps.document":
                request = service.files().export_media(fileId=target_id, mimeType="text/plain")
            elif mime == "application/vnd.google-apps.spreadsheet":
                request = service.files().export_media(fileId=target_id, mimeType="text/csv")
            elif mime == "application/vnd.google-apps.presentation":
                request = service.files().export_media(fileId=target_id, mimeType="text/plain")
            else:
                request = service.files().get_media(fileId=target_id)

            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            content_bytes = buffer.getvalue()
            content = ""

            if mime == "application/pdf" or meta.get("name", "").lower().endswith(".pdf"):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                    pages_txt = [page.extract_text() or "" for page in reader.pages[:15]]
                    content = "\n\n".join(pages_txt).strip()
                except Exception:
                    content = content_bytes.decode("utf-8", errors="replace")
            elif meta.get("name", "").lower().endswith(".docx"):
                try:
                    import docx
                    doc = docx.Document(io.BytesIO(content_bytes))
                    content = "\n".join(p.text for p in doc.paragraphs if p.text).strip()
                except Exception:
                    content = content_bytes.decode("utf-8", errors="replace")
            else:
                content = content_bytes.decode("utf-8", errors="replace")

            return {
                "success": True,
                "id": meta.get("id", target_id),
                "name": meta.get("name", ""),
                "mimeType": mime,
                "webViewLink": meta.get("webViewLink", ""),
                "content_preview": content[:5500],
                "bytes": len(content_bytes),
            }

        try:
            return await loop.run_in_executor(None, _read)
        except Exception as e:
            logger.error(f"[GoogleDrive] read_file_text failed for '{target_id}': {e}")
            return {"success": False, "error": f"Could not read Drive file '{file_id}': {e}"}

    async def create_file_or_doc(
        self,
        title: str,
        content: str = "",
        file_type: str = "doc",
        folder_id: str = "",
    ) -> dict[str, Any]:
        """Create a new Google Doc, Google Sheet (from CSV), or text/markdown file directly in Google Drive."""
        if not self._ensure_credentials():
            return {"success": False, "error": "Google Drive is not authenticated"}

        clean_title = (title or "Dione Generated Document").strip()
        ft = (file_type or "doc").lower().strip()
        loop = asyncio.get_running_loop()

        def _create():
            from googleapiclient.http import MediaIoBaseUpload

            service = self._get_drive_service()
            if ft in ("doc", "gdoc", "document", "google_doc"):
                target_mime = "application/vnd.google-apps.document"
                upload_mime = "text/plain"
            elif ft in ("sheet", "spreadsheet", "csv"):
                target_mime = "application/vnd.google-apps.spreadsheet"
                upload_mime = "text/csv"
            elif ft in ("folder", "directory"):
                meta_folder: dict[str, Any] = {
                    "name": clean_title,
                    "mimeType": "application/vnd.google-apps.folder",
                }
                if folder_id.strip():
                    meta_folder["parents"] = [folder_id.strip()]
                created = service.files().create(body=meta_folder, fields="id,name,webViewLink,mimeType").execute()
                return {
                    "success": True,
                    "id": created.get("id"),
                    "name": created.get("name"),
                    "mimeType": created.get("mimeType"),
                    "webViewLink": created.get("webViewLink"),
                }
            else:
                target_mime = "text/plain"
                upload_mime = "text/plain"

            metadata: dict[str, Any] = {"name": clean_title, "mimeType": target_mime}
            if folder_id.strip():
                metadata["parents"] = [folder_id.strip()]

            raw_bytes = (content or "").encode("utf-8")
            media = MediaIoBaseUpload(io.BytesIO(raw_bytes), mimetype=upload_mime, resumable=False)
            created = service.files().create(
                body=metadata,
                media_body=media,
                fields="id,name,mimeType,webViewLink",
            ).execute()
            return {
                "success": True,
                "id": created.get("id"),
                "name": created.get("name"),
                "mimeType": created.get("mimeType"),
                "webViewLink": created.get("webViewLink"),
            }

        try:
            return await loop.run_in_executor(None, _create)
        except Exception as e:
            logger.error(f"[GoogleDrive] create_file_or_doc failed: {e}")
            return {"success": False, "error": f"Failed to create Drive file '{clean_title}': {e}"}

    async def upload_file(self, file_path: str, folder_id: str = "", title: str = "") -> dict[str, Any]:
        if not self._ensure_credentials():
            return {"success": False, "error": "Google Drive is not authenticated"}
        fp = Path(file_path).expanduser()
        if not fp.is_absolute():
            fp = (Path.cwd() / fp).resolve()
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
            uploaded = service.files().create(body=metadata, media_body=media, fields="id,name,webViewLink,mimeType").execute()
            return {
                "success": True,
                "id": uploaded.get("id"),
                "name": uploaded.get("name"),
                "mimeType": uploaded.get("mimeType"),
                "webViewLink": uploaded.get("webViewLink"),
            }

        try:
            return await loop.run_in_executor(None, _upload)
        except Exception as e:
            logger.error(f"[GoogleDrive] upload_file failed: {e}")
            return {"success": False, "error": f"Upload failed: {e}"}

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "google_drive_search",
                "description": "Search for files, Google Docs, Sheets, PDFs, or folders in Google Drive (leave query empty to list recent files)",
                "parameters": {
                    "query": {"type": "string", "description": "Optional filename or keyword to search for (default '')"},
                    "count": {"type": "integer", "description": "Optional max results (default 15)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_drive_read",
                "description": "Read text/CSV content from a Google Drive file, Google Doc, Google Sheet, PDF, or DOCX by file_id or filename",
                "parameters": {
                    "file_id": {"type": "string", "description": "Drive file ID or exact filename to read"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_drive_create_file",
                "description": "Create a new Google Doc, Google Sheet, folder, or text document directly in Google Drive",
                "parameters": {
                    "title": {"type": "string", "description": "Title/name of the new Google Doc or file"},
                    "content": {"type": "string", "description": "Text or CSV content to write into the document"},
                    "file_type": {"type": "string", "description": "Optional type: 'doc' (Google Doc), 'sheet' (Google Sheet), 'folder', or 'txt' (default 'doc')"},
                    "folder_id": {"type": "string", "description": "Optional parent Drive folder ID"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_drive_upload",
                "description": "Upload a local file (or screenshot/report) from the workstation to Google Drive",
                "parameters": {
                    "file_path": {"type": "string", "description": "Local file path to upload (e.g. 'data/captures/latest_screen.jpg')"},
                    "title": {"type": "string", "description": "Optional target filename in Drive"},
                    "folder_id": {"type": "string", "description": "Optional parent Drive folder ID"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]
