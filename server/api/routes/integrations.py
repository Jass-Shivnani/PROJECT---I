"""
Dione AI — Integration Routes (v4.0 Demo-Hardened Edition)

Manage external service integrations (Unified Google OAuth2, Gmail, Drive, Calendar, Photos,
WhatsApp, Telegram, Slack, Instagram) with full compatibility across both REST conventions
(`/api/integrations/`, `/api/integrations/status`, `/api/integrations/google/connect`,
`/api/integrations/google/oauth`, `/api/integrations/{integration_id}/connect`, and `/api/integrations/connect`).
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class IntegrationConnectRequest(BaseModel):
    params: dict = {}
    service_id: Optional[str] = None
    credentials: Optional[dict] = None
    client_secret_path: Optional[str] = None
    access_token: Optional[str] = None


class IntegrationPermissionRequest(BaseModel):
    permissions: list[str] = []


class IntegrationToolRequest(BaseModel):
    tool_name: str
    params: dict = {}


def _format_registry_response(integrations) -> dict:
    if not integrations:
        return {"total": 0, "connected": 0, "integrations": []}
    data = integrations.to_dict()
    for item in data.get("integrations", []):
        if "service_id" not in item and "id" in item:
            item["service_id"] = item["id"]
        if "connected" not in item:
            item["connected"] = (item.get("status") == "connected")
    return data


@router.get("/")
@router.get("/status")
async def list_integrations(request: Request):
    integrations = getattr(request.app.state, "integrations", None)
    return _format_registry_response(integrations)


@router.post("/google/connect")
@router.post("/google/oauth")
async def connect_unified_google(body: IntegrationConnectRequest, request: Request):
    """One-click Unified Google OAuth2 login across Gmail, Calendar, Drive, and Photos."""
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "connected": False, "error": "Integrations are not initialized"}

    merged_params = dict(body.params or {})
    if body.credentials:
        merged_params.update(body.credentials)
    if body.client_secret_path:
        merged_params["client_secret_path"] = body.client_secret_path
    if body.access_token:
        merged_params["access_token"] = body.access_token

    res = await integrations.connect_google_unified(merged_params)
    res["connected"] = bool(res.get("success"))
    if res["connected"]:
        res["message"] = f"Connected Unified Google Workspace ({', '.join(res.get('connected_services', []))})"
    else:
        res["message"] = res.get("error", "Unified Google OAuth2 requires client_secret.json or access_token.")
    return res


@router.post("/connect")
async def connect_integration_by_body(body: IntegrationConnectRequest, request: Request):
    """Connect an integration specified by `service_id` in the request body."""
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "connected": False, "error": "Integrations are not initialized"}

    service_id = (body.service_id or "").strip()
    merged_params = dict(body.params or {})
    if body.credentials:
        merged_params.update(body.credentials)
    if not service_id:
        return await connect_unified_google(body, request)

    res = await integrations.connect(service_id, merged_params)
    res["connected"] = bool(res.get("success"))
    res["message"] = f"Connected {service_id}" if res["connected"] else (res.get("error") or f"Failed to connect {service_id}")
    return res


@router.post("/verify-all")
async def verify_all_integrations(request: Request):
    """Live-probe all registered integrations and return updated statuses."""
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "error": "Integrations are not initialized"}

    statuses = await integrations.verify_all_statuses()
    return {
        "success": True,
        "statuses": {k: v.value for k, v in statuses.items()},
        "registry": _format_registry_response(integrations),
    }


@router.post("/execute-tool")
async def execute_integration_tool(body: IntegrationToolRequest, request: Request):
    """Execute an integration tool directly via REST API."""
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "error": "Integrations are not initialized"}
    try:
        res = await integrations.execute_tool(body.tool_name, body.params or {})
        return {"success": True, "result": res}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/{integration_id}/grant")
async def grant_permissions(integration_id: str, body: IntegrationPermissionRequest, request: Request):
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "error": "Integrations are not initialized"}

    if not integrations.get_integration(integration_id):
        return {"success": False, "error": f"Unknown integration: {integration_id}"}

    result = integrations.grant_permissions(
        integration_id=integration_id,
        permission_names=body.permissions or None,
    )

    return {
        "success": len(result["failed"]) == 0,
        "granted": result["granted"],
        "failed": result["failed"],
    }


@router.post("/{integration_id}/connect")
async def connect_integration(integration_id: str, body: IntegrationConnectRequest, request: Request):
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "connected": False, "error": "Integrations are not initialized"}

    merged_params = dict(body.params or {})
    if body.credentials:
        merged_params.update(body.credentials)
    res = await integrations.connect(integration_id, merged_params)
    res["connected"] = bool(res.get("success"))
    return res


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(integration_id: str, request: Request):
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "error": "Integrations are not initialized"}

    return await integrations.disconnect(integration_id)


@router.post("/{integration_id}/sync")
async def sync_integration(integration_id: str, request: Request):
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "error": "Integrations are not initialized"}

    return await integrations.sync(integration_id)


@router.get("/tools")
async def list_integration_tools(request: Request):
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"tools": []}

    return {
        "tools": integrations.get_all_tools(),
        "connected_tools": integrations.get_tools(),
    }


@router.get("/{integration_id}/qr")
async def get_integration_qr(integration_id: str, request: Request):
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"success": False, "error": "Integrations are not initialized"}

    integration = integrations.get_integration(integration_id)
    if not integration:
        return {"success": False, "error": f"Unknown integration: {integration_id}"}

    if not hasattr(integration, "get_qr"):
        return {"success": False, "error": "This integration does not support QR login"}

    qr_data = await integration.get_qr()
    return {"success": True, "data": qr_data}
