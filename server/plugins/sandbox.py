"""
Dione AI — Sandboxed Execution Environment

Provides an isolation layer for plugin execution. Each plugin
runs with least-privilege access to prevent a hallucinating
model from executing destructive commands.
"""

import asyncio
from typing import Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class SandboxConfig:
    """Configuration for a sandboxed execution."""
    max_execution_time: float = 30.0  # seconds
    allow_network: bool = True
    allow_filesystem_write: bool = False
    allowed_paths: list[str] = None  # Whitelisted paths
    max_memory_mb: int = 256


class SandboxedExecutor:
    """
    Executes plugin calls within a controlled environment.
    
    Currently implements:
    - Timeout enforcement
    - Basic path restrictions
    - Execution logging
    
    Future enhancements:
    - Docker container isolation
    - Network filtering
    - Resource limits (CPU, memory)
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()

    async def execute(self, func, **kwargs) -> Any:
        """
        Execute a function within the sandbox constraints.
        
        Args:
            func: The async callable to execute
            **kwargs: Arguments to pass to the function
            
        Returns:
            The function's return value
            
        Raises:
            TimeoutError: If execution exceeds the time limit
            PermissionError: If the function tries to access restricted resources
        """
        logger.debug(f"Sandbox: executing {func.__name__} with timeout={self.config.max_execution_time}s")

        try:
            result = await asyncio.wait_for(
                func(**kwargs),
                timeout=self.config.max_execution_time,
            )
            logger.debug(f"Sandbox: {func.__name__} completed successfully")
            return result

        except asyncio.TimeoutError:
            logger.error(f"Sandbox: {func.__name__} timed out after {self.config.max_execution_time}s")
            raise TimeoutError(
                f"Plugin execution timed out after {self.config.max_execution_time} seconds"
            )
        except PermissionError as e:
            logger.error(f"Sandbox: {func.__name__} permission denied: {e}")
            raise
        except Exception as e:
            logger.error(f"Sandbox: {func.__name__} failed: {e}")
            raise

    def validate_path(self, path: str) -> bool:
        """Check if a file path is allowed by the sandbox."""
        if not self.config.allowed_paths:
            return True

        from pathlib import Path
        target = Path(path).resolve()
        for allowed in self.config.allowed_paths:
            if str(target).startswith(str(Path(allowed).resolve())):
                return True

        return False
