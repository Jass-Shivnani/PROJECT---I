"""
Dione AI — Integration Routes

Manage external service integrations (Gmail, Drive, etc.)
with runtime permission grants and connection lifecycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class IntegrationConnectRequest(BaseModel):
    params: dict = {}


class IntegrationPermissionRequest(BaseModel):
    permissions: list[str] = []


@router.get("/")
async def list_integrations(request: Request):
    integrations = getattr(request.app.state, "integrations", None)
    if not integrations:
        return {"total": 0, "connected": 0, "integrations": []}

    return integrations.to_dict()


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
        return {"success": False, "error": "Integrations are not initialized"}

    return await integrations.connect(integration_id, body.params or {})


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
