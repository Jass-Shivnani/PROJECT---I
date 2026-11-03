"""
Dione AI — Plugin & Integration Tool Routes

REST endpoints for listing and inspecting built-in plugins and external integration tools.
"""

from fastapi import APIRouter, Request, HTTPException
from dataclasses import asdict

router = APIRouter()


@router.get("/")
async def list_plugins(request: Request):
    """List all registered built-in plugin tools and integration tools."""
    registry = request.app.state.plugins
    integrations = getattr(request.app.state, "integrations", None)
    tools = list(registry.list_tools())
    if integrations:
        tools.extend(integrations.get_dione_tools_map().values())

    return {
        "plugins": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": [asdict(p) if hasattr(p, "__dataclass_fields__") else p for p in tool.parameters],
                "requires_confirmation": tool.requires_confirmation,
                "plugin_class": tool.plugin_class,
            }
            for tool in tools
        ],
        "total": len(tools),
    }


@router.get("/schemas/all")
async def get_all_schemas(request: Request):
    """Get JSON schemas for all tools (built-in + integrations)."""
    registry = request.app.state.plugins
    integrations = getattr(request.app.state, "integrations", None)
    tools = list(registry.list_tools())
    if integrations:
        tools.extend(integrations.get_dione_tools_map().values())
    return {
        "schemas": [tool.to_schema() for tool in tools],
        "total": len(tools),
    }


@router.get("/{tool_name}")
async def get_tool_info(tool_name: str, request: Request):
    """Get detailed information about a specific tool."""
    registry = request.app.state.plugins
    integrations = getattr(request.app.state, "integrations", None)
    tool = registry.get_tool(tool_name)
    if tool is None and integrations:
        tool = integrations.get_dione_tools_map().get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": [asdict(p) if hasattr(p, "__dataclass_fields__") else p for p in tool.parameters],
        "requires_confirmation": tool.requires_confirmation,
        "schema": tool.to_schema(),
    }
