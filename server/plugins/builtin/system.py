"""
Dione AI — System Plugin

Provides system-level operations: running commands, getting
system info, managing processes, and OS-level utilities.
"""

import platform
import subprocess
import asyncio
import psutil
from typing import Optional
from loguru import logger

from server.plugins.base import BasePlugin, dione_tool


class SystemPlugin(BasePlugin):
    """System-level operations and information."""

    name = "SystemPlugin"
    description = "Execute system commands and get system information"
    version = "0.1.0"

    @dione_tool(
        description="Get current system information (OS, CPU, RAM, disk)",
        permission_level="read",
    )
    async def system_info(self) -> str:
        """Get detailed system information."""
        info = {
            "os": f"{platform.system()} {platform.release()}",
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "ram_used_percent": psutil.virtual_memory().percent,
            "disk_total_gb": round(psutil.disk_usage("/").total / (1024**3), 1),
            "disk_used_percent": round(psutil.disk_usage("/").used / psutil.disk_usage("/").total * 100, 1),
        }

        lines = [f"  {k}: {v}" for k, v in info.items()]
        return "System Info:\n" + "\n".join(lines)

    @dione_tool(
        description="Run a shell command on the local machine",
        requires_confirmation=True,
        permission_level="execute",
    )
    async def run_command(self, command: str, timeout: int = 30) -> str:
        """Execute a shell command and return its output.
        
        :param command: The shell command to execute
        :param timeout: Maximum execution time in seconds
        """
        logger.info(f"Executing command: {command}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()

            result = f"Exit code: {process.returncode}\n"
            if output:
                result += f"Output:\n{output}\n"
            if errors:
                result += f"Errors:\n{errors}\n"

            return result

        except asyncio.TimeoutError:
            return f"Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Command failed: {str(e)}"

    @dione_tool(
        description="Get the current date and time",
        permission_level="read",
    )
    async def get_datetime(self) -> str:
        """Get the current date, time, and timezone."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S (%A, %B %d)")

    @dione_tool(
        description="List running processes",
        permission_level="read",
    )
    async def list_processes(self, top_n: int = 10) -> str:
        """List top processes by CPU/memory usage.
        
        :param top_n: Number of top processes to show
        """
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by memory usage
        processes.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
        top = processes[:top_n]

        lines = [f"Top {top_n} processes by memory:"]
        for p in top:
            lines.append(
                f"  PID {p['pid']}: {p['name']} "
                f"(CPU: {p.get('cpu_percent', 0):.1f}%, "
                f"RAM: {p.get('memory_percent', 0):.1f}%)"
            )

        return "\n".join(lines)
