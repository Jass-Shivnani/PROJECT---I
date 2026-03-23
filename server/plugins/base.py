"""
Dione AI — Plugin Base Class & Decorator

Provides the @dione_tool decorator that automatically converts
Python functions into tools the LLM can understand. Inspired by
OpenAI's function calling schema.
"""

import inspect
import functools
from typing import Callable, Optional, Any, get_type_hints
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ToolParameter:
    """A single parameter of a tool."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[list] = None


@dataclass
class DioneTool:
    """
    Represents a registered tool that the LLM can call.
    
    Generated automatically from decorated Python functions.
    """
    name: str                          # e.g., "GmailPlugin.send_email"
    description: str                   # From docstring
    parameters: list[ToolParameter]    # From function signature
    plugin_class: str                  # Parent plugin class name
    method_name: str                   # Actual method name
    func: Callable                     # The actual callable
    requires_confirmation: bool = False
    permission_level: str = "read"     # read, write, execute

    def to_schema(self) -> dict:
        """Convert to JSON schema for the LLM system prompt."""
        params = {}
        required = []
        for p in self.parameters:
            params[p.name] = {
                "type": p.type,
                "description": p.description,
            }
            if p.enum:
                params[p.name]["enum"] = p.enum
            if p.required:
                required.append(p.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": params,
                "required": required,
            },
        }


def _python_type_to_json(python_type) -> str:
    """Convert Python type annotations to JSON schema types."""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    
    # Handle Optional types
    origin = getattr(python_type, "__origin__", None)
    if origin is not None:
        args = getattr(python_type, "__args__", ())
        if origin is list:
            return "array"
        if origin is dict:
            return "object"
        # Optional[X] = Union[X, None]
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _python_type_to_json(non_none[0])

    return type_map.get(python_type, "string")


def dione_tool(
    description: Optional[str] = None,
    requires_confirmation: bool = False,
    permission_level: str = "read",
):
    """
    Decorator to register a method as a Dione tool.
    
    Usage:
        class MyPlugin(BasePlugin):
            @dione_tool(description="Read latest emails", permission_level="read")
            async def read_emails(self, count: int = 5, folder: str = "inbox"):
                '''Fetch the latest emails from the specified folder.'''
                ...
    
    The decorator:
    1. Extracts parameter info from the function signature
    2. Extracts description from the docstring (or decorator arg)
    3. Stores metadata so the PluginRegistry can find it
    """
    def decorator(func: Callable) -> Callable:
        # Extract type hints
        hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
        sig = inspect.signature(func)

        # Build parameter list (skip 'self')
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = hints.get(param_name, str)
            json_type = _python_type_to_json(param_type)
            is_required = param.default is inspect.Parameter.empty
            default_val = None if is_required else param.default

            # Try to extract param description from docstring
            param_desc = f"Parameter: {param_name}"
            if func.__doc__:
                # Look for ":param name:" or "Args:\n    name:" patterns
                import re
                pattern = rf"(?::param\s+{param_name}:|{param_name}\s*[:\-])\s*(.+)"
                match = re.search(pattern, func.__doc__)
                if match:
                    param_desc = match.group(1).strip()

            parameters.append(ToolParameter(
                name=param_name,
                type=json_type,
                description=param_desc,
                required=is_required,
                default=default_val,
            ))

        # Store metadata on the function
        func._dione_tool_meta = {
            "description": description or (func.__doc__ or "").strip().split("\n")[0],
            "parameters": parameters,
            "requires_confirmation": requires_confirmation,
            "permission_level": permission_level,
        }

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._dione_tool_meta = func._dione_tool_meta
        return wrapper

    return decorator


class BasePlugin:
    """
    Base class for all Dione plugins.
    
    Subclass this and use @dione_tool to register methods:
    
        class GmailPlugin(BasePlugin):
            name = "GmailPlugin"
            description = "Interact with Gmail"
            
            @dione_tool(description="Send an email")
            async def send_email(self, to: str, subject: str, body: str):
                ...
    """
    
    name: str = "BasePlugin"
    description: str = "Base plugin"
    version: str = "0.1.0"

    async def initialize(self):
        """Called when the plugin is first loaded. Override to set up connections."""
        pass

    async def shutdown(self):
        """Called when the plugin is being unloaded. Override to clean up."""
        pass

    def get_tools(self) -> list[DioneTool]:
        """Discover all @dione_tool decorated methods in this plugin."""
        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if callable(attr) and hasattr(attr, "_dione_tool_meta"):
                meta = attr._dione_tool_meta
                tool = DioneTool(
                    name=f"{self.name}.{attr_name}",
                    description=meta["description"],
                    parameters=meta["parameters"],
                    plugin_class=self.name,
                    method_name=attr_name,
                    func=attr,
                    requires_confirmation=meta["requires_confirmation"],
                    permission_level=meta["permission_level"],
                )
                tools.append(tool)
        return tools
