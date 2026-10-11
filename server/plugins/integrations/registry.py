"""
Integration Registry and Management
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from server.plugins.types import (
    AuthType, IntegrationStatus, IntegrationCredentials, HookEvent, IntegrationHookContext
)
from server.plugins.hooks import HookRunner
from server.plugins.permissions import PermissionManager, Permission
from .base import CredentialVault, BaseIntegration, IntegrationDisconnectedError
from .google_drive import GoogleDriveIntegration
from .google_photos import GooglePhotosIntegration
from .google_mail import GoogleMailIntegration
from .google_calendar import GoogleCalendarIntegration
from .slack import SlackIntegration
from .instagram import InstagramIntegration
from .whatsapp import WhatsAppIntegration
from .telegram import TelegramIntegration

ALL_INTEGRATIONS: list[type[BaseIntegration]] = [
    GoogleDriveIntegration,
    GooglePhotosIntegration,
    GoogleMailIntegration,
    GoogleCalendarIntegration,
    SlackIntegration,
    InstagramIntegration,
    WhatsAppIntegration,
    TelegramIntegration,
]


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
            integration.status = IntegrationStatus.DISCONNECTED
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
        tools = [
            {
                "name": "connect_integration",
                "description": "Trigger connection, pairing, or authentication for an external integration service (whatsapp, telegram, google_mail, slack, google_drive, google_calendar, instagram).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "The service name: whatsapp, telegram, google_mail, slack, google_drive, google_calendar, instagram",
                            "enum": ["whatsapp", "telegram", "google_mail", "slack", "google_drive", "google_calendar", "instagram"],
                        }
                    },
                    "required": ["service"],
                },
            }
        ]
        for integration in self._integrations.values():
            tools.extend(integration.get_tools())
        return tools

    def has_tool(self, tool_name: str) -> bool:
        """Check if any integration exposes a tool name."""
        if tool_name == "connect_integration":
            return True
        for integration in self._integrations.values():
            if any(t.get("name") == tool_name for t in integration.get_tools()):
                return True
        return False

    async def execute_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Execute an integration-owned tool by name."""
        if tool_name == "connect_integration":
            service = str(params.get("service", "")).lower().strip()
            if "tele" in service:
                service = "telegram"
            elif "what" in service:
                service = "whatsapp"
            elif "mail" in service or "gmail" in service:
                service = "google_mail"
            elif "drive" in service:
                service = "google_drive"
            elif "cal" in service:
                service = "google_calendar"
            elif "slack" in service:
                service = "slack"
            elif "insta" in service:
                service = "instagram"

            integ = self.get_integration(service)
            dname = integ.DISPLAY_NAME if integ else service.title()
            raise IntegrationDisconnectedError(
                integration_id=service,
                display_name=dname,
                tool_name="connect_integration",
                params=params,
            )

        for integration in self._integrations.values():
            for tool in integration.get_tools():
                if tool.get("name") != tool_name:
                    continue

                if integration.status != IntegrationStatus.CONNECTED:
                    live_status = await self.verify_status(integration.INTEGRATION_ID)
                    if live_status != IntegrationStatus.CONNECTED:
                        raise IntegrationDisconnectedError(
                            integration_id=integration.INTEGRATION_ID,
                            display_name=integration.DISPLAY_NAME,
                            tool_name=tool_name,
                            params=params,
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
            chat_id_value = str(params.get("chat_id", "")).strip()
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

            if (not to_value and not chat_id_value) or (not text_value and not file_path):
                raise RuntimeError("whatsapp_send requires ('to' or 'chat_id') and either 'text' or 'file_path'")

            result = await integration.send_message(
                to=to_value,
                chat_id=chat_id_value,
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
            chat_id_value = str(params.get("chat_id", "")).strip()
            file_path, matched = self._resolve_file_from_params(params)
            if (not to_value and not chat_id_value) or not file_path:
                raise RuntimeError("whatsapp_send_file requires ('to' or 'chat_id') and 'file_path'")

            caption_value = str(params.get("caption") or params.get("text") or "").strip()
            mime_type = str(params.get("mime_type", "")).strip()
            result = await integration.send_message(
                to=to_value,
                chat_id=chat_id_value,
                text="",
                file_path=file_path,
                caption=caption_value,
                mime_type=mime_type,
            )
            if matched and isinstance(result, dict):
                result["matched_files"] = matched
            return result

        if tool_name == "telegram_send" and hasattr(integration, "send_message"):
            text = str(params.get("text") or params.get("message") or "").strip()
            chat_id = str(params.get("chat_id") or "").strip()
            if not text:
                raise RuntimeError("telegram_send requires 'text'")
            return await integration.send_message(text=text, chat_id=chat_id)

        if tool_name == "telegram_send_file" and hasattr(integration, "send_file"):
            file_path, _ = self._resolve_file_from_params(params)
            if not file_path:
                file_path = str(params.get("file_path") or params.get("file") or "").strip()
            chat_id = str(params.get("chat_id") or "").strip()
            caption = str(params.get("caption") or "").strip()
            if not file_path:
                raise RuntimeError("telegram_send_file requires 'file_path'")
            return await integration.send_file(file_path=file_path, chat_id=chat_id, caption=caption)

        if tool_name == "telegram_read" and hasattr(integration, "read_messages"):
            limit = int(params.get("limit", 5))
            return await integration.read_messages(limit=limit)

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

    async def verify_status(self, integration_id: str) -> IntegrationStatus:
        """Probe the integration to verify its true live connection status."""
        integ = self._integrations.get(integration_id)
        if not integ:
            return IntegrationStatus.DISCONNECTED
        if not integ.credentials:
            integ.status = IntegrationStatus.DISCONNECTED
            return IntegrationStatus.DISCONNECTED

        try:
            is_active = await integ.test_connection()
            integ.status = IntegrationStatus.CONNECTED if is_active else IntegrationStatus.DISCONNECTED
        except Exception as e:
            logger.debug(f"Status check failed for {integration_id}: {e}")
            integ.status = IntegrationStatus.DISCONNECTED

        return integ.status

    async def verify_all_statuses(self) -> dict[str, IntegrationStatus]:
        """Probe all registered integrations and update their live connection status."""
        results = {}
        for iid in list(self._integrations.keys()):
            results[iid] = await self.verify_status(iid)
        return results


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


def create_default_registry(data_dir: str = "data") -> IntegrationRegistry:
    """Create and pre-register all built-in integrations."""
    vault = CredentialVault(data_dir=data_dir)
    permissions = PermissionManager(data_dir=data_dir)
    hooks = HookRunner()
    registry = IntegrationRegistry(vault=vault, permissions=permissions, hooks=hooks, data_dir=data_dir)
    for integration_class in ALL_INTEGRATIONS:
        registry.register(integration_class())
    return registry
