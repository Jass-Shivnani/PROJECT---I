"""
Dione AI — Plugin Routes

REST endpoints for listing and managing plugins/tools.
"""

from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/")
async def list_plugins(request: Request):
    """List all registered plugins and their tools."""
    registry = request.app.state.plugins
    tools = registry.list_tools()
    return {
        "plugins": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "requires_confirmation": tool.requires_confirmation,
            }
            for tool in tools
        ],
        "total": len(tools),
    }


@router.get("/{tool_name}")
async def get_tool_info(tool_name: str, request: Request):
    """Get detailed information about a specific tool."""
    registry = request.app.state.plugins
    tool = registry.get_tool(tool_name)
    if tool is None:
        return {"error": f"Tool '{tool_name}' not found"}, 404
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,
        "requires_confirmation": tool.requires_confirmation,
        "schema": tool.to_schema(),
    }


@router.get("/schemas/all")
async def get_all_schemas(request: Request):
    """Get JSON schemas for all tools (used by the LLM)."""
    registry = request.app.state.plugins
    tools = registry.list_tools()
    return {
        "schemas": [tool.to_schema() for tool in tools],
    }
