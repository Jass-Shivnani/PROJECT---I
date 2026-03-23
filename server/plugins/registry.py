"""
Dione AI — Plugin Registry

Dynamically loads plugins from the plugins directory, registers
their tools, and routes tool calls to the correct plugin method.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from server.plugins.base import BasePlugin, DioneTool


class PluginRegistry:
    """
    Dynamic plugin loader and tool router.
    
    Scans the plugins/builtin/ directory for Python modules that
    contain BasePlugin subclasses. Automatically registers all
    @dione_tool decorated methods.
    """

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}
        self._tools: dict[str, DioneTool] = {}

    @property
    def tools(self) -> dict[str, DioneTool]:
        return self._tools

    async def load_plugins(self, plugins_dir: str = None):
        """
        Scan a directory for plugin modules and load them.
        
        Each module should contain a class that extends BasePlugin.
        """
        if plugins_dir is None:
            plugins_dir = str(
                Path(__file__).parent / "builtin"
            )

        plugins_path = Path(plugins_dir)
        if not plugins_path.exists():
            logger.warning(f"Plugins directory not found: {plugins_dir}")
            return

        logger.info(f"Scanning for plugins in: {plugins_dir}")

        # Import each .py file in the directory
        for file in plugins_path.glob("*.py"):
            if file.name.startswith("_"):
                continue

            module_name = f"server.plugins.builtin.{file.stem}"
            try:
                module = importlib.import_module(module_name)
                
                # Find all BasePlugin subclasses in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BasePlugin)
                        and attr is not BasePlugin
                    ):
                        await self._register_plugin(attr)
                        
            except Exception as e:
                logger.error(f"Failed to load plugin from {file.name}: {e}")

        logger.info(
            f"Loaded {len(self._plugins)} plugins with {len(self._tools)} tools"
        )

    async def _register_plugin(self, plugin_class: type):
        """Instantiate a plugin and register its tools."""
        try:
            plugin = plugin_class()
            await plugin.initialize()

            self._plugins[plugin.name] = plugin

            # Register all tools from this plugin
            for tool in plugin.get_tools():
                self._tools[tool.name] = tool
                logger.debug(f"  Registered tool: {tool.name}")

        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")

    def get_tools_schema(self) -> list[dict]:
        """Get JSON schemas for all registered tools (for the LLM prompt)."""
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, params: dict) -> Any:
        """
        Execute a tool by name with the given parameters.
        
        Args:
            tool_name: Full tool name (e.g., "GmailPlugin.send_email")
            params: Dictionary of parameters to pass to the tool
            
        Returns:
            The tool's return value
            
        Raises:
            KeyError: If the tool is not found
            Exception: If the tool execution fails
        """
        tool = self._tools.get(tool_name)
        if not tool:
            available = ", ".join(self._tools.keys())
            raise KeyError(
                f"Tool '{tool_name}' not found. Available tools: {available}"
            )

        logger.info(f"Executing: {tool_name}({params})")
        
        try:
            result = await tool.func(**params)
            logger.info(f"Tool {tool_name} completed successfully")
            return result
        except TypeError as e:
            # Parameter mismatch
            logger.error(f"Parameter error in {tool_name}: {e}")
            raise ValueError(
                f"Invalid parameters for {tool_name}: {e}. "
                f"Expected: {[p.name for p in tool.parameters]}"
            )

    async def shutdown(self):
        """Gracefully shut down all plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.shutdown()
                logger.debug(f"Plugin {name} shut down")
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")

    def list_plugins(self) -> list[dict]:
        """List all loaded plugins and their tools."""
        result = []
        for name, plugin in self._plugins.items():
            tools = [t.name for t in plugin.get_tools()]
            result.append({
                "name": name,
                "description": plugin.description,
                "version": plugin.version,
                "tools": tools,
            })
        return result
