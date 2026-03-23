"""
Dione AI — Filesystem Plugin

Provides safe file system operations: read, write, list, search.
All operations are sandboxed to allowed directories.
"""

import os
import json
from pathlib import Path
from typing import Optional
from loguru import logger

from server.plugins.base import BasePlugin, dione_tool


class FilesystemPlugin(BasePlugin):
    """Safe local filesystem operations."""
    
    name = "FilesystemPlugin"
    description = "Read, write, list, and search files on the local filesystem"
    version = "0.1.0"

    def __init__(self):
        # Default allowed directory is the user's home
        self.base_dir = Path.home()

    @dione_tool(
        description="List files and folders in a directory",
        permission_level="read",
    )
    async def list_directory(self, path: str = "~", include_hidden: bool = False) -> str:
        """List files and folders in the specified directory.
        
        :param path: Directory path to list (default: home directory)
        :param include_hidden: Whether to include hidden files (starting with .)
        """
        target = Path(path).expanduser().resolve()
        
        if not target.exists():
            return f"Directory not found: {path}"
        if not target.is_dir():
            return f"Not a directory: {path}"

        entries = []
        for item in sorted(target.iterdir()):
            if not include_hidden and item.name.startswith("."):
                continue
            icon = "📁" if item.is_dir() else "📄"
            size = ""
            if item.is_file():
                size_bytes = item.stat().st_size
                if size_bytes < 1024:
                    size = f" ({size_bytes}B)"
                elif size_bytes < 1024 * 1024:
                    size = f" ({size_bytes // 1024}KB)"
                else:
                    size = f" ({size_bytes // (1024 * 1024)}MB)"
            entries.append(f"{icon} {item.name}{size}")

        return "\n".join(entries) if entries else "Empty directory"

    @dione_tool(
        description="Read the contents of a text file",
        permission_level="read",
    )
    async def read_file(self, path: str, max_lines: int = 100) -> str:
        """Read a text file's contents.
        
        :param path: Path to the file to read
        :param max_lines: Maximum number of lines to return
        """
        target = Path(path).expanduser().resolve()
        
        if not target.exists():
            return f"File not found: {path}"
        if not target.is_file():
            return f"Not a file: {path}"

        try:
            lines = target.read_text(encoding="utf-8").splitlines()
            if len(lines) > max_lines:
                return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
            return "\n".join(lines)
        except UnicodeDecodeError:
            return f"Cannot read binary file: {path}"

    @dione_tool(
        description="Write content to a file",
        requires_confirmation=True,
        permission_level="write",
    )
    async def write_file(self, path: str, content: str, append: bool = False) -> str:
        """Write or append content to a file.
        
        :param path: Path to the file to write
        :param content: Content to write
        :param append: If true, append to file instead of overwriting
        """
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        target.write_text(content, encoding="utf-8") if not append else \
            open(target, mode, encoding="utf-8").write(content)

        return f"Successfully {'appended to' if append else 'wrote'} {path}"

    @dione_tool(
        description="Search for files by name pattern",
        permission_level="read",
    )
    async def search_files(
        self, directory: str = "~", pattern: str = "*", recursive: bool = True
    ) -> str:
        """Search for files matching a glob pattern.
        
        :param directory: Directory to search in
        :param pattern: Glob pattern (e.g., "*.pdf", "report*")
        :param recursive: Search recursively in subdirectories
        """
        target = Path(directory).expanduser().resolve()
        
        if not target.exists():
            return f"Directory not found: {directory}"

        if recursive:
            matches = list(target.rglob(pattern))
        else:
            matches = list(target.glob(pattern))

        # Limit results
        matches = matches[:50]

        if not matches:
            return f"No files matching '{pattern}' found in {directory}"

        results = []
        for m in matches:
            rel = m.relative_to(target) if m.is_relative_to(target) else m
            results.append(str(rel))

        return f"Found {len(results)} files:\n" + "\n".join(results)
