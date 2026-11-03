"""
Integration Registry and Management
Provides Unified Google OAuth2 SSO across Gmail, Calendar, Drive, and Photos,
complete tool dispatch across all 8 integrations, auto-permission grants,
and typed callable tool wrappers for DioneEngine's native function calling.
"""

from __future__ import annotations

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from loguru import logger

from server.plugins.types import (
    AuthType, IntegrationStatus, IntegrationCredentials, HookEvent, IntegrationHookContext
)
from server.plugins.hooks import HookRunner
from server.plugins.permissions import PermissionManager, Permission
from server.plugins.base import DioneTool, ToolParameter
from .base import CredentialVault, BaseIntegration, IntegrationDisconnectedError
from .google_oauth import GOOGLE_SERVICE_IDS, UNIFIED_GOOGLE_SCOPES, run_unified_google_oauth
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
    Manages all registered integrations (Gmail, Drive, Calendar, Photos, WhatsApp, Telegram, Slack, Instagram).
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

        pruned = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        matches: list[tuple[int, str]] = []
        for path in root.rglob("*"):
            if any(part in pruned for part in path.parts):
                continue
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
        """Register an integration and auto-grant default permissions if not yet set."""
        iid = integration.INTEGRATION_ID
        if iid in self._integrations:
            logger.warning(f"Integration already registered: {iid}")
            return
        
        self._integrations[iid] = integration

        # Ensure required permissions are granted so user doesn't hit permission errors on first connect
        for perm in integration.REQUIRED_PERMISSIONS:
            if not self._permissions.check(iid, perm):
                self._permissions.grant(iid, perm, granted_by="system_bootstrap", reason="Default integration capability")
        
        # Restore credentials if available
        creds = self._vault.retrieve(iid)
        if creds:
            integration.credentials = creds
            integration.status = IntegrationStatus.CONNECTED
            logger.info(f"Restored credentials for integration: {iid} (marked ready)")
        
        logger.info(f"Integration registered: {iid} ({integration.DISPLAY_NAME})")

    async def initialize_saved_connections(self) -> dict[str, str]:
        """Verify all integrations that have saved credentials or environment tokens on startup."""
        # Auto-bootstrap Telegram if env token is present
        tg = self._integrations.get("telegram")
        if tg and not tg.credentials:
            import os
            token = (os.getenv("DIONE_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
            if token:
                await self.connect("telegram", {"bot_token": token, "chat_id": os.getenv("DIONE_TELEGRAM_CHAT_ID", "")})

        results = {}
        for iid, integ in self._integrations.items():
            if integ.credentials:
                status = await self.verify_status(iid)
                results[iid] = status.value
        return results

    async def connect_google_unified(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        One-click Unified Google OAuth2 login.
        Authenticates once with combined scopes and connects Gmail, Google Calendar,
        Google Drive, and Google Photos simultaneously.
        """
        oauth_creds = await run_unified_google_oauth(params, scopes=UNIFIED_GOOGLE_SCOPES)
        if not oauth_creds:
            return {
                "success": False,
                "error": "Unified Google OAuth2 failed. Provide access_token, client_id+client_secret, or place client_secret.json in data/credentials/client_secret.json.",
            }

        self._vault.store("google_unified", oauth_creds)
        connected_services = []
        errors = {}

        for gid in GOOGLE_SERVICE_IDS:
            integ = self._integrations.get(gid)
            if not integ:
                continue
            service_creds = IntegrationCredentials(
                integration_id=gid,
                auth_type=AuthType.OAUTH2,
                access_token=oauth_creds.access_token,
                refresh_token=oauth_creds.refresh_token,
                token_expiry=oauth_creds.token_expiry,
                extra=dict(oauth_creds.extra or {}),
            )
            integ.credentials = service_creds
            self._vault.store(gid, service_creds)
            ok = await integ.test_connection()
            if ok:
                integ.status = IntegrationStatus.CONNECTED
                integ.error_message = None
                connected_services.append(gid)
            else:
                # Still mark connected if token is valid OAuth2 but specific API isn't enabled yet in GCP
                integ.status = IntegrationStatus.CONNECTED
                connected_services.append(gid)
                errors[gid] = "Token stored (verify API is enabled in Google Cloud Console if calls fail)"

        return {
            "success": len(connected_services) > 0,
            "connected_services": connected_services,
            "notes": errors,
        }
    
    async def connect(self, integration_id: str, params: dict[str, Any]) -> dict:
        """Connect an integration with permission checks and unified Google propagation."""
        if integration_id in ("google", "google_unified"):
            return await self.connect_google_unified(params)

        integration = self._integrations.get(integration_id)
        if not integration:
            return {"success": False, "error": f"Unknown integration: {integration_id}"}
        
        # Ensure permissions are granted
        for perm in integration.REQUIRED_PERMISSIONS:
            if not self._permissions.check(integration_id, perm):
                self._permissions.grant(integration_id, perm, granted_by="user", reason="Connect integration")
        
        # Run connect hook
        hook_ctx = IntegrationHookContext(
            event=HookEvent.ON_INTEGRATION_CONNECT,
            plugin_id=integration_id,
            integration_id=integration_id,
            integration_name=integration.DISPLAY_NAME,
            event_type="connect",
            event_data={"params": {k: "***" if "key" in k or "pass" in k or "token" in k else v for k, v in params.items()}},
        )
        await self._hooks.run(HookEvent.ON_INTEGRATION_CONNECT, hook_ctx)
        
        # Connect
        success = await integration.connect(params)
        
        if success and integration.credentials:
            self._vault.store(integration_id, integration.credentials)
            # If user authenticated any Google service via OAuth2, propagate to all other Google services!
            if (
                integration_id in GOOGLE_SERVICE_IDS
                and integration.credentials.auth_type == AuthType.OAUTH2
                and integration.credentials.access_token
                and params.get("propagate_google", True)
            ):
                self._vault.store("google_unified", integration.credentials)
                for other_gid in GOOGLE_SERVICE_IDS:
                    if other_gid == integration_id:
                        continue
                    other_integ = self._integrations.get(other_gid)
                    if other_integ and other_integ.status != IntegrationStatus.CONNECTED:
                        shared = IntegrationCredentials(
                            integration_id=other_gid,
                            auth_type=AuthType.OAUTH2,
                            access_token=integration.credentials.access_token,
                            refresh_token=integration.credentials.refresh_token,
                            token_expiry=integration.credentials.token_expiry,
                            extra=dict(integration.credentials.extra or {}),
                        )
                        other_integ.credentials = shared
                        other_integ.status = IntegrationStatus.CONNECTED
                        self._vault.store(other_gid, shared)
        
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
        """Disconnect an integration (or all Google services if google_unified)."""
        if integration_id in ("google", "google_unified"):
            for gid in GOOGLE_SERVICE_IDS:
                await self.disconnect(gid)
            self._vault.delete("google_unified")
            return {"success": True, "status": "disconnected"}

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
        
        if integration.status != IntegrationStatus.CONNECTED and not integration.credentials:
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
            if integration.status == IntegrationStatus.CONNECTED or integration.credentials is not None:
                tools.extend(integration.get_tools())
        return tools

    def get_all_tools(self) -> list[dict]:
        """Get all tools from all integrations, connected or not."""
        tools = [
            {
                "name": "connect_integration",
                "description": "Check status or initiate connection/authentication for an external integration service (google_unified, google_mail, google_calendar, google_drive, google_photos, whatsapp, telegram, slack, instagram).",
                "parameters": {
                    "service": {
                        "type": "string",
                        "description": "The service name: google_unified, google_mail, google_calendar, google_drive, google_photos, whatsapp, telegram, slack, instagram",
                    }
                },
            }
        ]
        for integration in self._integrations.values():
            tools.extend(integration.get_tools())
        return tools

    def get_dione_tools_map(self) -> dict[str, DioneTool]:
        """
        Builds a dictionary of DioneTool objects for all integration tools so
        DioneEngine and PluginRegistry can expose them natively to Gemini/OpenAI/Ollama.
        """
        tool_map: dict[str, DioneTool] = {}
        for t_def in self.get_all_tools():
            t_name = t_def.get("name", "")
            if not t_name:
                continue
            t_desc = t_def.get("description", f"Execute {t_name}")
            raw_params = t_def.get("parameters", {})
            if "properties" in raw_params and isinstance(raw_params.get("properties"), dict):
                props = raw_params["properties"]
            else:
                props = raw_params

            params_list: list[ToolParameter] = []
            for p_name, p_info in (props or {}).items():
                if not isinstance(p_info, dict):
                    continue
                p_type = p_info.get("type", "string")
                p_desc = p_info.get("description", f"Parameter {p_name}")
                is_req = not ("optional" in p_desc.lower() or "default" in p_desc.lower())
                params_list.append(
                    ToolParameter(
                        name=p_name,
                        type=p_type,
                        description=p_desc,
                        required=is_req,
                    )
                )

            def _make_exec_fn(bound_tool_name: str, bound_desc: str, bound_params: list[ToolParameter]):
                import inspect

                async def _integration_tool_fn(**kwargs):
                    res = await self.execute_tool(bound_tool_name, kwargs)
                    if isinstance(res, (dict, list)):
                        return json.dumps(res, indent=2, default=str)
                    return str(res)

                _integration_tool_fn.__name__ = bound_tool_name
                _integration_tool_fn.__doc__ = bound_desc

                # Build explicit inspect.Signature so google-genai SDK extracts exact typed parameters
                type_map = {
                    "string": str,
                    "integer": int,
                    "number": float,
                    "boolean": bool,
                    "array": list,
                    "object": dict,
                }
                sig_params = []
                annotations = {}
                for p in sorted(bound_params, key=lambda x: not x.required):
                    py_t = type_map.get(p.type, str)
                    annotations[p.name] = py_t if p.required else Optional[py_t]
                    sig_params.append(
                        inspect.Parameter(
                            name=p.name,
                            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            default=inspect.Parameter.empty if p.required else None,
                            annotation=annotations[p.name],
                        )
                    )
                annotations["return"] = str
                _integration_tool_fn.__annotations__ = annotations
                _integration_tool_fn.__signature__ = inspect.Signature(parameters=sig_params, return_annotation=str)
                return _integration_tool_fn

            fn = _make_exec_fn(t_name, t_desc, params_list)
            is_send_or_delete = any(k in t_name for k in ("send", "delete", "create", "upload"))
            tool_map[t_name] = DioneTool(
                name=t_name,
                description=t_desc,
                parameters=params_list,
                plugin_class="IntegrationRegistry",
                method_name=t_name,
                func=fn,
                requires_confirmation=False,
                permission_level="execute" if is_send_or_delete else "read",
            )
        return tool_map

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
            elif "photo" in service:
                service = "google_photos"
            elif "slack" in service:
                service = "slack"
            elif "insta" in service:
                service = "instagram"
            elif "google" in service:
                return await self.connect_google_unified(params)

            integ = self.get_integration(service)
            if not integ:
                return {"success": False, "error": f"Unknown integration service: {service}"}
            if integ.credentials:
                live = await self.verify_status(service)
                return {"service": service, "status": live.value, "connected": live == IntegrationStatus.CONNECTED}
            return {
                "service": service,
                "status": "disconnected",
                "connected": False,
                "instructions": f"Please connect {integ.DISPLAY_NAME} in Settings -> Integrations & Channels (or POST /api/integrations/{service}/connect).",
            }

        for integration in self._integrations.values():
            for tool in integration.get_tools():
                if tool.get("name") != tool_name:
                    continue

                if integration.status != IntegrationStatus.CONNECTED:
                    # Check if unified Google credentials were added since startup
                    if not integration.credentials:
                        restored = self._vault.retrieve(integration.INTEGRATION_ID)
                        if restored:
                            integration.credentials = restored
                    live_status = await self.verify_status(integration.INTEGRATION_ID)
                    if live_status != IntegrationStatus.CONNECTED:
                        # For Gmail tools, gracefully fall back to EmailPlugin if available
                        if integration.INTEGRATION_ID == "google_mail" and tool_name in ("gmail_send", "gmail_send_file", "gmail_read"):
                            from server.plugins.builtin.email_plugin import EmailPlugin
                            ep = EmailPlugin()
                            if tool_name in ("gmail_send", "gmail_send_file"):
                                fp, _ = self._resolve_file_from_params(params)
                                return await ep.send_email(
                                    to=str(params.get("to", "")),
                                    subject=str(params.get("subject", "Message from Dione")),
                                    body=str(params.get("body", "")),
                                    attachments=[fp] if fp else params.get("attachments"),
                                )
                            elif tool_name == "gmail_read":
                                return await ep.read_emails(count=int(params.get("count", 5)))
                        return {
                            "success": False,
                            "integration": integration.INTEGRATION_ID,
                            "status": "disconnected",
                            "error": f"{integration.DISPLAY_NAME} is not connected yet. Connect it in Settings -> Integrations & Channels.",
                        }

                return await self._dispatch_tool(integration, tool_name, params)

        raise KeyError(f"Unknown integration tool: {tool_name}")

    async def _dispatch_tool(self, integration: BaseIntegration, tool_name: str, params: dict[str, Any]) -> Any:
        """Dispatch integration tools to concrete integration methods across all 8 integrations."""
        # --- Gmail ---
        if tool_name == "gmail_read" and hasattr(integration, "read_emails"):
            return await integration.read_emails(
                count=int(params.get("count") or 5),
                unread_only=bool(params.get("unread_only") or False),
            )

        if tool_name == "gmail_search" and hasattr(integration, "search_emails"):
            return await integration.search_emails(
                query=str(params.get("query") or "").strip(),
                count=int(params.get("count") or 10),
            )

        if tool_name == "gmail_send" and hasattr(integration, "send_email"):
            attachments = params.get("attachments") or []
            if isinstance(attachments, str):
                attachments = [attachments]
            if not isinstance(attachments, list):
                attachments = []

            file_path, matched = self._resolve_file_from_params(params)
            if file_path:
                attachments = [file_path, *[a for a in attachments if a != file_path]]

            result = await integration.send_email(
                to=str(params.get("to") or "").strip(),
                subject=str(params.get("subject") or "").strip(),
                body=str(params.get("body") or "").strip(),
                attachments=[str(a).strip() for a in attachments if str(a).strip()],
            )
            if matched and isinstance(result, dict):
                result["matched_files"] = matched
            return result

        if tool_name == "gmail_send_file" and hasattr(integration, "send_email"):
            to_value = str(params.get("to") or "").strip()
            file_path, matched = self._resolve_file_from_params(params)
            if not to_value or not file_path:
                raise RuntimeError("gmail_send_file requires both 'to' and 'file_path' (or 'file_query')")

            subject_value = str(params.get("subject") or "File from Dione").strip() or "File from Dione"
            body_value = str(params.get("body") or "Attached file from Dione.").strip()
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

        # --- Google Drive ---
        if tool_name == "google_drive_search" and hasattr(integration, "list_files"):
            return await integration.list_files(
                query=str(params.get("query") or "").strip(),
                count=int(params.get("count") or 10),
            )

        if tool_name == "google_drive_read" and hasattr(integration, "read_file_text"):
            return await integration.read_file_text(
                file_id=str(params.get("file_id") or "").strip()
            )

        if tool_name == "google_drive_upload" and hasattr(integration, "upload_file"):
            file_path, _ = self._resolve_file_from_params(params)
            return await integration.upload_file(
                file_path=file_path or str(params.get("file_path") or "").strip(),
                folder_id=str(params.get("folder_id") or "").strip(),
                title=str(params.get("title") or "").strip(),
            )

        # --- Google Calendar ---
        if tool_name == "calendar_events" and hasattr(integration, "list_events"):
            return await integration.list_events(
                days=int(params.get("days") or 7),
                query=str(params.get("query") or "").strip(),
            )

        if tool_name == "calendar_create" and hasattr(integration, "create_event"):
            attendees = params.get("attendees") or []
            if isinstance(attendees, str):
                attendees = [a.strip() for a in attendees.split(",") if a.strip()]
            return await integration.create_event(
                title=str(params.get("title") or "").strip(),
                start=str(params.get("start") or "").strip(),
                end=str(params.get("end") or "").strip(),
                description=str(params.get("description") or "").strip(),
                location=str(params.get("location") or "").strip(),
                attendees=attendees,
            )

        if tool_name == "calendar_delete" and hasattr(integration, "delete_event"):
            return await integration.delete_event(
                event_id=str(params.get("event_id") or "").strip()
            )

        # --- Google Photos ---
        if tool_name == "google_photos_search" and hasattr(integration, "search_photos"):
            return await integration.search_photos(
                query=str(params.get("query") or "").strip(),
                count=int(params.get("count") or 10),
            )

        if tool_name == "google_photos_memories" and hasattr(integration, "get_memories"):
            return await integration.get_memories()

        # --- Slack ---
        if tool_name == "slack_send" and hasattr(integration, "send_message"):
            return await integration.send_message(
                channel=str(params.get("channel") or "").strip(),
                text=str(params.get("text") or params.get("message") or "").strip(),
            )

        if tool_name == "slack_read" and hasattr(integration, "read_messages"):
            return await integration.read_messages(
                channel=str(params.get("channel") or "").strip(),
                count=int(params.get("count") or 10),
            )

        if tool_name == "slack_channels" and hasattr(integration, "list_channels"):
            return await integration.list_channels()

        # --- Instagram ---
        if tool_name == "instagram_profile" and hasattr(integration, "sync"):
            return await integration.sync()

        if tool_name == "instagram_posts" and hasattr(integration, "get_recent_posts"):
            return await integration.get_recent_posts(
                count=int(params.get("count") or 5)
            )

        # --- WhatsApp ---
        if tool_name == "whatsapp_send" and hasattr(integration, "send_message"):
            to_value = str(params.get("to") or "").strip()
            chat_id_value = str(params.get("chat_id") or "").strip()
            text_value = str(
                params.get("text")
                or params.get("message")
                or params.get("body")
                or ""
            ).strip()
            file_path, matched = self._resolve_file_from_params(params)
            if not file_path:
                file_path = str(params.get("file") or "").strip()
            caption = str(params.get("caption") or "").strip()
            mime_type = str(params.get("mime_type") or "").strip()

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
            to_value = str(params.get("to") or "").strip()
            chat_id_value = str(params.get("chat_id") or "").strip()
            file_path, matched = self._resolve_file_from_params(params)
            if (not to_value and not chat_id_value) or not file_path:
                raise RuntimeError("whatsapp_send_file requires ('to' or 'chat_id') and 'file_path'")

            caption_value = str(params.get("caption") or params.get("text") or "").strip()
            mime_type = str(params.get("mime_type") or "").strip()
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

        # --- Telegram ---
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
            limit = int(params.get("limit") or 5)
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
            restored = self._vault.retrieve(integration_id)
            if restored:
                integ.credentials = restored
            else:
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
            "unified_google_connected": all(
                self._integrations.get(gid) and self._integrations[gid].status == IntegrationStatus.CONNECTED
                for gid in GOOGLE_SERVICE_IDS
            ),
            "integrations": self.list_integrations(),
        }


def create_default_registry(data_dir: str = "data") -> IntegrationRegistry:
    """Create and pre-register all built-in integrations."""
    vault = CredentialVault(data_dir=data_dir)
    permissions = PermissionManager(data_dir=data_dir)
    hooks = HookRunner()
    registry = IntegrationRegistry(vault=vault, permissions=permissions, hooks=hooks, data_dir=data_dir)
    for integration_class in ALL_INTEGRATIONS:
        registry.register(integration_class())
    return registry
