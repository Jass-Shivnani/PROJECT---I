"""
Dione AI -- Base Integration and Credential Management
"""

from __future__ import annotations

import json
import hashlib
import secrets
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from server.plugins.types import (
    AuthType, IntegrationStatus, IntegrationConfig,
    IntegrationCredentials, HookEvent, IntegrationHookContext,
)
from server.plugins.hooks import HookRunner
from server.plugins.permissions import PermissionManager, Permission


class IntegrationDisconnectedError(RuntimeError):
    """Raised when a tool is called on an integration that is currently disconnected."""
    def __init__(self, integration_id: str, display_name: str, tool_name: str, params: dict = None):
        self.integration_id = integration_id
        self.display_name = display_name
        self.tool_name = tool_name
        self.params = params or {}
        super().__init__(f"Integration '{display_name}' ({integration_id}) is not connected.")


class CredentialVault:
    """
    Credential storage with Unified Google OAuth2 fallback and legacy path compatibility.
    """
    
    GOOGLE_SERVICES = {"google_mail", "google_calendar", "google_drive", "google_photos"}

    def __init__(self, data_dir: str = "data"):
        self._base_data_dir = Path(data_dir)
        self._dir = self._base_data_dir / "credentials"
        self._legacy_dir = self._base_data_dir / "integrations"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._legacy_dir.mkdir(parents=True, exist_ok=True)
    
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
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Credentials stored for integration: {integration_id}")
    
    def _load_file(self, path: Path, integration_id: str) -> Optional[IntegrationCredentials]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw_auth = data.get("auth_type", "oauth2" if data.get("access_token") else "api_key")
            return IntegrationCredentials(
                integration_id=integration_id,
                auth_type=AuthType(raw_auth),
                access_token=data.get("access_token"),
                refresh_token=data.get("refresh_token"),
                token_expiry=(
                    datetime.fromisoformat(data["token_expiry"])
                    if data.get("token_expiry")
                    else None
                ),
                api_key=data.get("api_key") or data.get("app_password"),
                extra=data.get("extra", {k: v for k, v in data.items() if k not in ("auth_type", "access_token", "refresh_token", "token_expiry", "api_key")}),
            )
        except Exception as e:
            logger.error(f"Failed to retrieve credentials for {integration_id} from {path}: {e}")
            return None

    def retrieve(self, integration_id: str) -> Optional[IntegrationCredentials]:
        """Retrieve credentials for an integration, checking direct, unified Google, and legacy paths."""
        path = self._dir / f"{integration_id}.json"
        if path.exists():
            return self._load_file(path, integration_id)

        # Check unified Google OAuth2 credential if this is a Google service
        if integration_id in self.GOOGLE_SERVICES:
            unified_path = self._dir / "google_unified.json"
            if unified_path.exists():
                return self._load_file(unified_path, integration_id)

        # Check legacy data/integrations/{integration_id}.json
        legacy_path = self._legacy_dir / f"{integration_id}.json"
        if legacy_path.exists():
            return self._load_file(legacy_path, integration_id)

        return None
    
    def delete(self, integration_id: str) -> bool:
        """Delete stored credentials."""
        deleted = False
        for d in (self._dir, self._legacy_dir):
            path = d / f"{integration_id}.json"
            if path.exists():
                path.unlink()
                deleted = True
        if deleted:
            logger.info(f"Credentials deleted for: {integration_id}")
        return deleted
    
    def list_stored(self) -> list[str]:
        """List all integration IDs with stored credentials."""
        return [p.stem for p in self._dir.glob("*.json")]


class BaseIntegration(ABC):
    """
    Abstract base class for all service integrations.
    """
    
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
        ...
    
    @abstractmethod
    async def test_connection(self) -> bool:
        ...
    
    @abstractmethod
    async def sync(self) -> dict[str, Any]:
        ...
    
    @abstractmethod
    def get_tools(self) -> list[dict]:
        ...
    
    async def connect(self, params: dict[str, Any]) -> bool:
        """Full connection flow: authenticate -> test -> sync."""
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
            "has_credentials": self.credentials is not None,
        }
