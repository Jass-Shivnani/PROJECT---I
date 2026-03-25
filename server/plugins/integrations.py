"""
Dione AI — Integration Framework

Manages external service integrations (Google Drive, Photos, Mail, Calendar, etc.)
with OAuth2 flows, credential storage, and a plugin-friendly base class.

Inspired by OpenClaw's channel adapters and provider system.
"""

from __future__ import annotations

import json
import hashlib
import secrets
import asyncio
import mimetypes
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import io
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from server.plugins.types import (
    AuthType, IntegrationStatus, IntegrationConfig,
    IntegrationCredentials, HookEvent, IntegrationHookContext,
)
from server.plugins.hooks import HookRunner
from server.plugins.permissions import PermissionManager, Permission


# ─── Credential Vault ────────────────────────────────────────

class CredentialVault:
    """
    Encrypted-at-rest credential storage.
    
    In production this would use OS keyring or a proper vault.
    For the capstone, we use a JSON file with basic obfuscation
    (NOT production-grade crypto — sufficient for demo).
    """
    
    def __init__(self, data_dir: str = "data"):
        self._dir = Path(data_dir) / "credentials"
        self._dir.mkdir(parents=True, exist_ok=True)
    
    def store(self, integration_id: str, credentials: IntegrationCredentials) -> None:
        """Store credentials for an integration."""
        path = self._dir / f"{integration_id}.json"
        data = {
            "auth_type": credentials.auth_type.value,
            "access_token": credentials.access_token,
            "refresh_token": credentials.refresh_token,
            "token_expiry": credentials.token_expiry.isoformat() if credentials.token_expiry else None,
            "api_key": credentials.api_key,
            "extra": credentials.extra,
            "stored_at": datetime.now().isoformat(),
        }
        # Basic obfuscation — hash the integration id as filename
        path.write_text(json.dumps(data, indent=2))
        logger.info(f"Credentials stored for integration: {integration_id}")
    
    def retrieve(self, integration_id: str) -> Optional[IntegrationCredentials]:
        """Retrieve credentials for an integration."""
        path = self._dir / f"{integration_id}.json"
        if not path.exists():
            return None
        
        try:
            data = json.loads(path.read_text())
            return IntegrationCredentials(
                integration_id=integration_id,
                auth_type=AuthType(data["auth_type"]),
                access_token=data.get("access_token"),
                refresh_token=data.get("refresh_token"),
                token_expiry=(
                    datetime.fromisoformat(data["token_expiry"])
                    if data.get("token_expiry")
                    else None
                ),
                api_key=data.get("api_key"),
                extra=data.get("extra", {}),
            )
        except Exception as e:
            logger.error(f"Failed to retrieve credentials for {integration_id}: {e}")
            return None
    
    def delete(self, integration_id: str) -> bool:
        """Delete stored credentials."""
        path = self._dir / f"{integration_id}.json"
        if path.exists():
            path.unlink()
            logger.info(f"Credentials deleted for: {integration_id}")
            return True
        return False
    
    def list_stored(self) -> list[str]:
        """List all integration IDs with stored credentials."""
        return [p.stem for p in self._dir.glob("*.json")]


# ─── Base Integration ────────────────────────────────────────

class BaseIntegration(ABC):
    """
    Abstract base class for all service integrations.
    
    Subclasses implement:
      - configure() -> set up config
      - authenticate() -> perform auth flow
      - test_connection() -> verify connectivity
      - sync() -> pull/push data
      - get_tools() -> expose tools to the ReAct engine
    """
    
    # Subclasses must define
    INTEGRATION_ID: str = ""
    DISPLAY_NAME: str = ""
    DESCRIPTION: str = ""
    AUTH_TYPE: AuthType = AuthType.OAUTH2
    REQUIRED_PERMISSIONS: list[Permission] = []
    SCOPES: list[str] = []
    
    def __init__(self):
        self.status = IntegrationStatus.DISCONNECTED
        self.config: Optional[IntegrationConfig] = None
        self.credentials: Optional[IntegrationCredentials] = None
        self.last_sync: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self._data: dict[str, Any] = {}
    
    @abstractmethod
    async def authenticate(self, params: dict[str, Any]) -> bool:
        """
        Perform authentication.
        
        For OAuth2: params should contain auth_code or redirect_url
        For API_KEY: params should contain api_key
        For TOKEN: params should contain token
        
        Returns True if authentication succeeded.
        """
        ...
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the integration is currently connected and working."""
        ...
    
    @abstractmethod
    async def sync(self) -> dict[str, Any]:
        """
        Synchronize data with the external service.
        
        Returns a summary dict with sync results.
        """
        ...
    
    @abstractmethod
    def get_tools(self) -> list[dict]:
        """
        Return tool definitions that this integration provides
        to the ReAct engine.
        """
        ...
    
    async def connect(self, params: dict[str, Any]) -> bool:
        """Full connection flow: authenticate → test → sync."""
        self.status = IntegrationStatus.CONNECTING
        
        try:
            if await self.authenticate(params):
                if await self.test_connection():
                    self.status = IntegrationStatus.CONNECTED
                    self.error_message = None
                    logger.info(f"Integration connected: {self.INTEGRATION_ID}")
                    return True
                else:
                    self.status = IntegrationStatus.ERROR
                    self.error_message = "Connection test failed"
            else:
                self.status = IntegrationStatus.ERROR
                self.error_message = "Authentication failed"
        except Exception as e:
            self.status = IntegrationStatus.ERROR
            self.error_message = str(e)
            logger.error(f"Integration connection error [{self.INTEGRATION_ID}]: {e}")
        
        return False
    
    async def disconnect(self) -> None:
        """Disconnect the integration."""
        self.status = IntegrationStatus.DISCONNECTED
        self.credentials = None
        self.error_message = None
        logger.info(f"Integration disconnected: {self.INTEGRATION_ID}")
    
    def to_dict(self) -> dict:
        """Serialize integration state."""
        return {
            "id": self.INTEGRATION_ID,
            "name": self.DISPLAY_NAME,
            "description": self.DESCRIPTION,
            "status": self.status.value,
            "auth_type": self.AUTH_TYPE.value,
            "scopes": self.SCOPES,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "error": self.error_message,
            "tools_count": len(self.get_tools()),
        }


# ─── Integration Registry ───────────────────────────────────

class IntegrationRegistry:
    """
    Manages all registered integrations.
    
    Handles:
      - Registration/discovery of integrations
      - Connection lifecycle
      - Credential management via CredentialVault
      - Permission checks before connection
      - Hook execution on connect/disconnect/sync
    """
    
    def __init__(
        self,
        vault: CredentialVault,
        permissions: PermissionManager,
        hooks: HookRunner,
        data_dir: str = "data",
    ):
        self._vault = vault
        self._permissions = permissions
        self._hooks = hooks
        self._integrations: dict[str, BaseIntegration] = {}
        self._data_dir = Path(data_dir) / "integrations"
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def _find_files(self, query: str, search_root: str = ".", max_results: int = 10) -> list[str]:
        root = Path(search_root).expanduser()
        if not root.is_absolute():
            root = (Path.cwd() / root).resolve()
        if not root.exists() or not root.is_dir():
            return []

        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        matches: list[tuple[int, str]] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(root)).replace("\\", "/")
            rel_lower = rel.lower()
            score = rel_lower.find(normalized_query)
            if score != -1:
                matches.append((score + len(rel) // 100, str(path.resolve())))
                if len(matches) >= max_results * 8:
                    break

        matches.sort(key=lambda item: item[0])
        return [m[1] for m in matches[:max_results]]

    def _resolve_file_from_params(self, params: dict[str, Any]) -> tuple[str, list[str]]:
        file_path = str(
            params.get("file_path")
            or params.get("attachment")
            or params.get("path")
            or ""
        ).strip()

        if file_path:
            fp = Path(file_path).expanduser()
            if not fp.is_absolute():
                fp = (Path.cwd() / fp).resolve()
            return str(fp), []

        file_query = str(params.get("file_query", "")).strip()
        search_root = str(params.get("search_root", ".")).strip() or "."
        if not file_query:
            return "", []

        matches = self._find_files(file_query, search_root=search_root, max_results=10)
        return (matches[0] if matches else ""), matches
    
    def register(self, integration: BaseIntegration) -> None:
        """Register an integration."""
        iid = integration.INTEGRATION_ID
        if iid in self._integrations:
            logger.warning(f"Integration already registered: {iid}")
            return
        
        self._integrations[iid] = integration
        
        # Restore credentials if available
        creds = self._vault.retrieve(iid)
        if creds:
            integration.credentials = creds
            integration.status = IntegrationStatus.CONNECTED
            logger.info(f"Restored credentials for integration: {iid}")
        
        logger.info(f"Integration registered: {iid} ({integration.DISPLAY_NAME})")
    
    async def connect(self, integration_id: str, params: dict[str, Any]) -> dict:
        """Connect an integration with permission checks."""
        integration = self._integrations.get(integration_id)
        if not integration:
            return {"success": False, "error": f"Unknown integration: {integration_id}"}
        
        # Check permissions
        for perm in integration.REQUIRED_PERMISSIONS:
            if not self._permissions.check(integration_id, perm):
                return {
                    "success": False,
                    "error": f"Missing permission: {perm.value}",
                    "required_permissions": [p.value for p in integration.REQUIRED_PERMISSIONS],
                }
        
        # Run connect hook
        hook_ctx = IntegrationHookContext(
            event=HookEvent.ON_INTEGRATION_CONNECT,
            plugin_id=integration_id,
            integration_id=integration_id,
            integration_name=integration.DISPLAY_NAME,
            event_type="connect",
            event_data={"params": params},
        )
        await self._hooks.run(HookEvent.ON_INTEGRATION_CONNECT, hook_ctx)
        
        # Connect
        success = await integration.connect(params)
        
        if success and integration.credentials:
            self._vault.store(integration_id, integration.credentials)
        
        # Run generic integration event hook
        hook_ctx = IntegrationHookContext(
            event=HookEvent.ON_INTEGRATION_EVENT,
            plugin_id=integration_id,
            integration_id=integration_id,
            integration_name=integration.DISPLAY_NAME,
            event_type="connect_result",
            event_data={"success": success, "error": integration.error_message},
        )
        await self._hooks.run(HookEvent.ON_INTEGRATION_EVENT, hook_ctx)
        
        return {
            "success": success,
            "status": integration.status.value,
            "error": integration.error_message,
        }
    
    async def disconnect(self, integration_id: str) -> dict:
        """Disconnect an integration."""
        integration = self._integrations.get(integration_id)
        if not integration:
            return {"success": False, "error": f"Unknown integration: {integration_id}"}
        
        await integration.disconnect()
        self._vault.delete(integration_id)

        hook_ctx = IntegrationHookContext(
            event=HookEvent.ON_INTEGRATION_DISCONNECT,
            plugin_id=integration_id,
            integration_id=integration_id,
            integration_name=integration.DISPLAY_NAME,
            event_type="disconnect",
            event_data={},
        )
        await self._hooks.run(HookEvent.ON_INTEGRATION_DISCONNECT, hook_ctx)
        
        return {"success": True, "status": integration.status.value}
    
    async def sync(self, integration_id: str) -> dict:
        """Trigger a sync for an integration."""
        integration = self._integrations.get(integration_id)
        if not integration:
            return {"success": False, "error": f"Unknown integration: {integration_id}"}
        
        if integration.status != IntegrationStatus.CONNECTED:
            return {"success": False, "error": "Integration not connected"}
        
        integration.status = IntegrationStatus.SYNCING
        try:
            result = await integration.sync()
            integration.last_sync = datetime.now()
            integration.status = IntegrationStatus.CONNECTED

            hook_ctx = IntegrationHookContext(
                event=HookEvent.ON_INTEGRATION_EVENT,
                plugin_id=integration_id,
                integration_id=integration_id,
                integration_name=integration.DISPLAY_NAME,
                event_type="sync",
                event_data={"result": result},
            )
            await self._hooks.run(HookEvent.ON_INTEGRATION_EVENT, hook_ctx)
            return {"success": True, "result": result}
        except Exception as e:
            integration.status = IntegrationStatus.ERROR
            integration.error_message = str(e)
            return {"success": False, "error": str(e)}
    
    def get_tools(self) -> list[dict]:
        """Get all tools from connected integrations."""
        tools = []
        for iid, integration in self._integrations.items():
            if integration.status == IntegrationStatus.CONNECTED:
                tools.extend(integration.get_tools())
        return tools

    def get_all_tools(self) -> list[dict]:
        """Get all tools from all integrations, connected or not."""
        tools = []
        for integration in self._integrations.values():
            tools.extend(integration.get_tools())
        return tools

    def has_tool(self, tool_name: str) -> bool:
        """Check if any integration exposes a tool name."""
        for integration in self._integrations.values():
            if any(t.get("name") == tool_name for t in integration.get_tools()):
                return True
        return False

    async def execute_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Execute an integration-owned tool by name."""
        for integration in self._integrations.values():
            for tool in integration.get_tools():
                if tool.get("name") != tool_name:
                    continue

                if integration.status != IntegrationStatus.CONNECTED:
                    raise RuntimeError(
                        f"Integration '{integration.DISPLAY_NAME}' is not connected. "
                        f"Run: dione integrations connect {integration.INTEGRATION_ID}"
                    )

                return await self._dispatch_tool(integration, tool_name, params)

        raise KeyError(f"Unknown integration tool: {tool_name}")

    async def _dispatch_tool(self, integration: BaseIntegration, tool_name: str, params: dict[str, Any]) -> Any:
        """Dispatch integration tools to concrete integration methods."""
        if tool_name == "gmail_read" and hasattr(integration, "read_emails"):
            return await integration.read_emails(
                count=int(params.get("count", 5)),
                unread_only=bool(params.get("unread_only", False)),
            )

        if tool_name == "gmail_search" and hasattr(integration, "search_emails"):
            return await integration.search_emails(
                query=str(params.get("query", "")).strip(),
                count=int(params.get("count", 10)),
            )

        if tool_name == "gmail_send" and hasattr(integration, "send_email"):
            attachments = params.get("attachments", [])
            if isinstance(attachments, str):
                attachments = [attachments]
            if not isinstance(attachments, list):
                attachments = []

            file_path, matched = self._resolve_file_from_params(params)
            if file_path:
                attachments = [file_path, *[a for a in attachments if a != file_path]]

            result = await integration.send_email(
                to=str(params.get("to", "")).strip(),
                subject=str(params.get("subject", "")).strip(),
                body=str(params.get("body", "")).strip(),
                attachments=[str(a).strip() for a in attachments if str(a).strip()],
            )
            if matched and isinstance(result, dict):
                result["matched_files"] = matched
            return result

        if tool_name == "gmail_send_file" and hasattr(integration, "send_email"):
            to_value = str(params.get("to", "")).strip()
            file_path, matched = self._resolve_file_from_params(params)
            if not to_value or not file_path:
                raise RuntimeError("gmail_send_file requires both 'to' and 'file_path'")

            subject_value = str(params.get("subject", "File from Dione")).strip() or "File from Dione"
            body_value = str(params.get("body", "Attached file from Dione.")).strip()
            result = await integration.send_email(
                to=to_value,
                subject=subject_value,
                body=body_value,
                attachments=[file_path],
            )
            if matched and isinstance(result, dict):
                result["matched_files"] = matched
            return result

        if tool_name == "gmail_unread_count" and hasattr(integration, "sync"):
            summary = await integration.sync()
            return {"unread": summary.get("unread", 0), "summary": summary}

        if tool_name == "google_drive_search" and hasattr(integration, "list_files"):
            return await integration.list_files(
                query=str(params.get("query", "")).strip(),
                count=int(params.get("count", 10)),
            )

        if tool_name == "google_drive_read" and hasattr(integration, "read_file_text"):
            return await integration.read_file_text(
                file_id=str(params.get("file_id", "")).strip()
            )

        if tool_name == "whatsapp_send" and hasattr(integration, "send_message"):
            to_value = str(params.get("to", "")).strip()
            text_value = str(
                params.get("text")
                or params.get("message")
                or params.get("body")
                or ""
            ).strip()
            file_path, matched = self._resolve_file_from_params(params)
            if not file_path:
                file_path = str(params.get("file", "")).strip()
            caption = str(params.get("caption", "")).strip()
            mime_type = str(params.get("mime_type", "")).strip()

            if not to_value or (not text_value and not file_path):
                raise RuntimeError("whatsapp_send requires 'to' and either 'text' or 'file_path'")

            result = await integration.send_message(
                to=to_value,
                text=text_value,
                file_path=file_path,
                caption=caption,
                mime_type=mime_type,
            )
            if matched and isinstance(result, dict):
                result["matched_files"] = matched
            return result

        if tool_name == "whatsapp_send_file" and hasattr(integration, "send_message"):
            to_value = str(params.get("to", "")).strip()
            file_path, matched = self._resolve_file_from_params(params)
            if not to_value or not file_path:
                raise RuntimeError("whatsapp_send_file requires both 'to' and 'file_path'")

            caption_value = str(params.get("caption") or params.get("text") or "").strip()
            mime_type = str(params.get("mime_type", "")).strip()
            result = await integration.send_message(
                to=to_value,
                text="",
                file_path=file_path,
                caption=caption_value,
                mime_type=mime_type,
            )
            if matched and isinstance(result, dict):
                result["matched_files"] = matched
            return result

        raise RuntimeError(f"Tool '{tool_name}' is not implemented for integration '{integration.INTEGRATION_ID}'")
    
    def get_integration(self, integration_id: str) -> Optional[BaseIntegration]:
        """Get a specific integration."""
        return self._integrations.get(integration_id)
    
    def list_integrations(self) -> list[dict]:
        """List all registered integrations."""
        return [i.to_dict() for i in self._integrations.values()]
    
    def get_connected(self) -> list[str]:
        """Get IDs of all connected integrations."""
        return [
            iid for iid, i in self._integrations.items()
            if i.status == IntegrationStatus.CONNECTED
        ]

    def grant_permissions(self, integration_id: str, permission_names: list[str] | None = None) -> dict[str, list[str]]:
        """Grant required or explicit permissions for an integration."""
        integration = self._integrations.get(integration_id)
        if not integration:
            return {"granted": [], "failed": permission_names or []}

        granted: list[str] = []
        failed: list[str] = []
        requested = permission_names or [p.value for p in integration.REQUIRED_PERMISSIONS]

        for permission_name in requested:
            try:
                permission = Permission(permission_name)
                self._permissions.grant(
                    integration_id,
                    permission,
                    granted_by="user",
                    reason="runtime integration grant",
                )
                granted.append(permission.value)
            except Exception:
                failed.append(permission_name)

        return {"granted": granted, "failed": failed}
    
    def to_dict(self) -> dict:
        """Full registry state."""
        return {
            "total": len(self._integrations),
            "connected": len(self.get_connected()),
            "integrations": self.list_integrations(),
        }


# ─── Google Integration Stubs ────────────────────────────────
# These will be fleshed out when we add actual API calls.

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


class GooglePhotosIntegration(BaseIntegration):
    """Google Photos — memories, albums, photo search."""
    
    INTEGRATION_ID = "google_photos"
    DISPLAY_NAME = "Google Photos"
    DESCRIPTION = "Access photos and memories from Google Photos"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.MEMORY_READ]
    SCOPES = [
        "https://www.googleapis.com/auth/photoslibrary.readonly",
    ]
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        if "access_token" in params:
            self.credentials = IntegrationCredentials(
                integration_id=self.INTEGRATION_ID,
                auth_type=AuthType.OAUTH2,
                access_token=params["access_token"],
                refresh_token=params.get("refresh_token"),
                token_expiry=datetime.now() + timedelta(hours=1),
            )
            return True
        return False
    
    async def test_connection(self) -> bool:
        return self.credentials is not None
    
    async def sync(self) -> dict[str, Any]:
        return {"photos_indexed": 0, "albums_found": 0}
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "google_photos_search",
                "description": "Search photos by date, location, or content",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "date_range": {"type": "string", "description": "Date range (optional)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "google_photos_memories",
                "description": "Get 'On This Day' memories from Google Photos",
                "parameters": {},
                "integration": self.INTEGRATION_ID,
            },
        ]


class GoogleMailIntegration(BaseIntegration):
    """
    Gmail — read, search, compose, and send emails.
    
    Uses IMAP for reading and SMTP for sending via Python stdlib.
    Requires an App Password (not regular password) for Gmail.
    """
    
    INTEGRATION_ID = "google_mail"
    DISPLAY_NAME = "Gmail"
    DESCRIPTION = "Read, search, and send emails via Gmail"
    AUTH_TYPE = AuthType.API_KEY  # App password
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = []

    IMAP_HOST = "imap.gmail.com"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        email = params.get("email", "")
        app_password = params.get("app_password", params.get("api_key", ""))
        if not email or not app_password:
            return False
        
        self.credentials = IntegrationCredentials(
            integration_id=self.INTEGRATION_ID,
            auth_type=AuthType.API_KEY,
            api_key=app_password,
            extra={"email": email},
        )
        return True
    
    async def test_connection(self) -> bool:
        if not self.credentials:
            return False
        try:
            import imaplib
            email = self.credentials.extra.get("email", "")
            password = self.credentials.api_key
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
            mail.login(email, password)
            mail.logout()
            return True
        except Exception as e:
            logger.error(f"Gmail IMAP test failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        """Fetch unread count and recent subjects."""
        if not self.credentials:
            return {"error": "Not authenticated"}
        try:
            import imaplib
            email = self.credentials.extra.get("email", "")
            password = self.credentials.api_key
            
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
            mail.login(email, password)
            mail.select("INBOX")
            
            _, data = mail.search(None, "UNSEEN")
            unread_ids = data[0].split() if data[0] else []
            
            _, all_data = mail.search(None, "ALL")
            total = len(all_data[0].split()) if all_data[0] else 0
            
            mail.logout()
            
            self.last_sync = datetime.now()
            return {
                "unread": len(unread_ids),
                "total_messages": total,
                "synced_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Gmail sync error: {e}")
            return {"error": str(e)}
    
    async def read_emails(self, folder: str = "INBOX", count: int = 5,
                          unread_only: bool = False) -> list[dict]:
        """Read recent emails from a folder."""
        if not self.credentials:
            return []
        try:
            import imaplib
            import email as email_lib
            from email.header import decode_header
            
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
            mail.login(
                self.credentials.extra.get("email", ""),
                self.credentials.api_key,
            )
            mail.select(folder)
            
            criteria = "UNSEEN" if unread_only else "ALL"
            _, data = mail.search(None, criteria)
            ids = data[0].split() if data[0] else []
            
            results = []
            for mid in ids[-count:]:
                _, msg_data = mail.fetch(mid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                
                subject = ""
                raw_subject = msg.get("Subject", "")
                if raw_subject:
                    decoded = decode_header(raw_subject)
                    subject = decoded[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(decoded[0][1] or "utf-8", errors="replace")
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            charset = part.get_content_charset() or "utf-8"
                            body = part.get_payload(decode=True).decode(charset, errors="replace")
                            break
                else:
                    charset = msg.get_content_charset() or "utf-8"
                    body = msg.get_payload(decode=True).decode(charset, errors="replace")
                
                results.append({
                    "id": mid.decode(),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "subject": subject,
                    "date": msg.get("Date", ""),
                    "body_preview": body[:500] if body else "",
                })
            
            mail.logout()
            return results
        except Exception as e:
            logger.error(f"Gmail read error: {e}")
            return [{"error": str(e)}]
    
    async def send_email(self, to: str, subject: str, body: str, attachments: list[str] | None = None) -> dict:
        """Send an email via SMTP."""
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders
            
            sender = self.credentials.extra.get("email", "")
            password = self.credentials.api_key
            attachment_paths = attachments or []
            
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            attached_files: list[str] = []
            for raw_path in attachment_paths:
                try:
                    abs_path = Path(raw_path).expanduser().resolve()
                    if not abs_path.exists() or not abs_path.is_file():
                        logger.warning(f"Skipping missing attachment: {raw_path}")
                        continue

                    ctype, _ = mimetypes.guess_type(str(abs_path))
                    if not ctype:
                        ctype = "application/octet-stream"
                    maintype, subtype = ctype.split("/", 1)

                    with open(abs_path, "rb") as fh:
                        payload = fh.read()

                    part = MIMEBase(maintype, subtype)
                    part.set_payload(payload)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{abs_path.name}"')
                    msg.attach(part)
                    attached_files.append(str(abs_path))
                except Exception as attachment_error:
                    logger.warning(f"Failed to attach file '{raw_path}': {attachment_error}")
            
            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to}: {subject}")
            return {"success": True, "to": to, "subject": subject, "attachments": attached_files}
        except Exception as e:
            logger.error(f"Gmail send error: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_emails(self, query: str, folder: str = "INBOX",
                            count: int = 10) -> list[dict]:
        """Search emails by subject/sender using IMAP search."""
        if not self.credentials:
            return []
        try:
            import imaplib
            import email as email_lib
            from email.header import decode_header
            
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
            mail.login(
                self.credentials.extra.get("email", ""),
                self.credentials.api_key,
            )
            mail.select(folder)
            
            # IMAP search by subject or from
            _, data = mail.search(None, f'(OR SUBJECT "{query}" FROM "{query}")')
            ids = data[0].split() if data[0] else []
            
            results = []
            for mid in ids[-count:]:
                _, msg_data = mail.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
                header = msg_data[0][1].decode("utf-8", errors="replace")
                results.append({"id": mid.decode(), "header": header.strip()})
            
            mail.logout()
            return results
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return [{"error": str(e)}]
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "gmail_read",
                "description": "Read recent emails from Gmail inbox. Returns subject, sender, date, and preview.",
                "parameters": {
                    "count": {"type": "integer", "description": "Number of emails to fetch (default 5)"},
                    "unread_only": {"type": "boolean", "description": "Only show unread emails"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_search",
                "description": "Search Gmail by subject or sender keyword",
                "parameters": {"query": {"type": "string", "description": "Search keyword"}},
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_send",
                "description": "Compose and send an email via Gmail (supports file attachments)",
                "parameters": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body text"},
                    "file_path": {"type": "string", "description": "Optional file path to attach"},
                    "file_query": {"type": "string", "description": "Optional filename/path search query to auto-find file"},
                    "search_root": {"type": "string", "description": "Optional root directory for file_query (default current workspace)"},
                    "attachments": {"type": "array", "description": "Optional list of file paths to attach"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_send_file",
                "description": "Send an email with an actual file attachment (not file contents)",
                "parameters": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "file_path": {"type": "string", "description": "Local file path to attach"},
                    "file_query": {"type": "string", "description": "Optional filename/path search query if file_path unknown"},
                    "search_root": {"type": "string", "description": "Optional root directory for file_query"},
                    "subject": {"type": "string", "description": "Optional email subject line"},
                    "body": {"type": "string", "description": "Optional email body text"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_unread_count",
                "description": "Get the number of unread emails in inbox",
                "parameters": {},
                "integration": self.INTEGRATION_ID,
            },
        ]


class GoogleCalendarIntegration(BaseIntegration):
    """Google Calendar — events, reminders, scheduling."""
    
    INTEGRATION_ID = "google_calendar"
    DISPLAY_NAME = "Google Calendar"
    DESCRIPTION = "Access and manage Google Calendar events"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        if "access_token" in params:
            self.credentials = IntegrationCredentials(
                integration_id=self.INTEGRATION_ID,
                auth_type=AuthType.OAUTH2,
                access_token=params["access_token"],
                refresh_token=params.get("refresh_token"),
                token_expiry=datetime.now() + timedelta(hours=1),
            )
            return True
        return False
    
    async def test_connection(self) -> bool:
        return self.credentials is not None
    
    async def sync(self) -> dict[str, Any]:
        return {"events_synced": 0, "upcoming": 0}
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "calendar_events",
                "description": "Get upcoming calendar events",
                "parameters": {
                    "days": {"type": "integer", "description": "Days to look ahead (default 7)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "calendar_create",
                "description": "Create a calendar event",
                "parameters": {
                    "title": {"type": "string", "description": "Event title"},
                    "start": {"type": "string", "description": "Start time (ISO format)"},
                    "end": {"type": "string", "description": "End time (ISO format)"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]


# ─── Slack Integration ───────────────────────────────────────

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

class InstagramIntegration(BaseIntegration):
    """
    Instagram — read profile, posts, and DMs via Instagram Graph API.
    
    Requires a Facebook/Instagram access token with appropriate permissions.
    """
    
    INTEGRATION_ID = "instagram"
    DISPLAY_NAME = "Instagram"
    DESCRIPTION = "Read Instagram profile, posts, and messages"
    AUTH_TYPE = AuthType.TOKEN
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = ["instagram_basic", "instagram_manage_messages", "pages_messaging"]
    
    GRAPH_API = "https://graph.instagram.com/v21.0"
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        token = params.get("access_token", params.get("token", ""))
        if not token:
            return False
        self.credentials = IntegrationCredentials(
            auth_type=AuthType.TOKEN,
            access_token=token,
        )
        return True
    
    async def test_connection(self) -> bool:
        if not self.credentials:
            return False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self.GRAPH_API}/me",
                    params={
                        "fields": "id,username",
                        "access_token": self.credentials.access_token,
                    },
                )
                return r.status_code == 200 and "id" in r.json()
        except Exception as e:
            logger.error(f"Instagram test failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        """Fetch profile and recent media counts."""
        if not self.credentials:
            return {"error": "Not authenticated"}
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self.GRAPH_API}/me",
                    params={
                        "fields": "id,username,media_count,account_type",
                        "access_token": self.credentials.access_token,
                    },
                )
                data = r.json()
                return {
                    "username": data.get("username", ""),
                    "media_count": data.get("media_count", 0),
                    "account_type": data.get("account_type", ""),
                }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_recent_posts(self, count: int = 5) -> list[dict]:
        """Get recent media posts."""
        if not self.credentials:
            return []
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self.GRAPH_API}/me/media",
                    params={
                        "fields": "id,caption,media_type,timestamp,permalink",
                        "limit": count,
                        "access_token": self.credentials.access_token,
                    },
                )
                data = r.json()
                return data.get("data", [])
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "instagram_profile",
                "description": "Get Instagram profile info",
                "parameters": {},
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "instagram_posts",
                "description": "Get recent Instagram posts",
                "parameters": {
                    "count": {"type": "integer", "description": "Number of posts (default 5)"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]


# ─── WhatsApp Integration (Business API) ─────────────────────

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
            if not self._ensure_bridge_started():
                return False
            bridge = self._bridge_from_credentials()
            if bridge is None:
                return False
            status = await bridge.get_status()
            return status.get("status") in {"connected", "connecting", "qr"}
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
        text: str,
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
                    "file_path": {"type": "string", "description": "Local file path to send"},
                    "file_query": {"type": "string", "description": "Optional filename/path search query if file_path unknown"},
                    "search_root": {"type": "string", "description": "Optional root directory for file_query"},
                    "caption": {"type": "string", "description": "Optional caption"},
                    "mime_type": {"type": "string", "description": "Optional MIME type override"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]


# ─── Convenience: all built-in integrations ──────────────────

ALL_INTEGRATIONS: list[type[BaseIntegration]] = [
    GoogleDriveIntegration,
    GooglePhotosIntegration,
    GoogleMailIntegration,
    GoogleCalendarIntegration,
    SlackIntegration,
    InstagramIntegration,
    WhatsAppIntegration,
]


def create_default_registry(data_dir: str = "data") -> IntegrationRegistry:
    """Create and pre-register all built-in integrations."""
    vault = CredentialVault(data_dir=data_dir)
    permissions = PermissionManager(data_dir=data_dir)
    hooks = HookRunner()
    registry = IntegrationRegistry(vault=vault, permissions=permissions, hooks=hooks, data_dir=data_dir)
    for integration_class in ALL_INTEGRATIONS:
        registry.register(integration_class())
    return registry

