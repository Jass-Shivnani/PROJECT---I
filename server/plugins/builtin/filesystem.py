"""
Dione AI — Filesystem Plugin (Sovereign Edition)

Provides hardened local filesystem operations:
- Poset Lattice path safety guarding against system directory mutation
- Resilient text reading with offset line paging and encoding fallback
- Win32 Recycle Bin integration (soft deletion with undo capability)
- Pruned fast search avoiding deep vendor/cache trees (node_modules, .git, .venv)
- Comprehensive file and directory metadata inspection
"""

import os
import sys
import time
import shutil
import platform
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger

from server.plugins.base import BasePlugin, dione_tool
from server.core.safety import SafetyKernel, PermissionTier

# Windows Win32 Shell API for native Recycle Bin integration
if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.WORD),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]


class FilesystemPlugin(BasePlugin):
    """Safe local filesystem operations with Poset Lattice protection."""

    name = "FilesystemPlugin"
    description = "Read, write, search, and manage files on the local filesystem with safety guardrails"
    version = "0.2.0"

    # Directories excluded from deep search and protected from modification
    PRUNED_DIRECTORIES = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".idea",
        ".vscode",
        "$recycle.bin",
        "system volume information",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
    }

    def __init__(self):
        super().__init__()
        self._safety = SafetyKernel()

    def _is_path_protected(self, path: Path) -> Optional[str]:
        """Check if a path targets sensitive operating system or environment structures."""
        try:
            resolved = path.resolve()
            str_path = str(resolved).lower()

            # Prevent root deletion
            if str_path in ["c:\\", "/", "d:\\", "e:\\"]:
                return "Root directory cannot be modified or deleted."

            if platform.system() == "Windows":
                sys_root = os.environ.get("SystemRoot", "C:\\Windows").lower()
                prog_files = os.environ.get("ProgramFiles", "C:\\Program Files").lower()
                prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower()

                for protected in [sys_root, prog_files, prog_files_x86]:
                    if str_path == protected or str_path.startswith(protected + "\\"):
                        return f"Path is inside protected system location '{protected}'."

            # Protect active virtual environment from accidental wipe
            venv_path = Path(".venv").resolve()
            if resolved == venv_path or venv_path in resolved.parents:
                return "Modification or deletion of active virtual environment (.venv) is prohibited."

            return None
        except Exception as e:
            return f"Path resolution error: {e}"

    def _recycle_path(self, target: Path) -> bool:
        """Send a file or folder to the OS Recycle Bin (soft delete)."""
        if platform.system() == "Windows":
            target_str = str(target.resolve())
            # SHFileOperation requires double null-terminated string
            p_from = target_str + "\0\0"
            FO_DELETE = 0x0003
            FOF_ALLOWUNDO = 0x0040
            FOF_NOCONFIRMATION = 0x0010
            FOF_SILENT = 0x0004

            fileop = SHFILEOPSTRUCTW()
            fileop.hwnd = 0
            fileop.wFunc = FO_DELETE
            fileop.pFrom = p_from
            fileop.pTo = None
            fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
            fileop.fAnyOperationsAborted = False
            fileop.hNameMappings = None
            fileop.lpszProgressTitle = None

            res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
            return res == 0
        else:
            # Fallback for Unix/macOS: standard remove
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            return True

    @dione_tool(
        description="List files and folders in a directory with file sizes and types",
        permission_level="read",
    )
    async def list_directory(self, path: str = ".", include_hidden: bool = False) -> str:
        """List files and folders in the specified directory.
        
        :param path: Directory path to list (default: current working directory)
        :param include_hidden: Whether to include hidden files (starting with .)
        """
        try:
            target = Path(path).expanduser().resolve()

            if not target.exists():
                return f"Directory not found: {path}"
            if not target.is_dir():
                return f"Not a directory: {path}"

            entries = []
            for item in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if not include_hidden and item.name.startswith("."):
                    continue

                tag = "[DIR] " if item.is_dir() else "[FILE]"
                size_str = ""
                if item.is_file():
                    try:
                        sz = item.stat().st_size
                        if sz < 1024:
                            size_str = f" ({sz} B)"
                        elif sz < 1024 * 1024:
                            size_str = f" ({round(sz / 1024, 1)} KB)"
                        else:
                            size_str = f" ({round(sz / (1024 * 1024), 1)} MB)"
                    except Exception:
                        size_str = ""

                entries.append(f"  {tag} {item.name}{size_str}")

            header = f"Directory contents of: {target} ({len(entries)} items)"
            return header + "\n" + ("\n".join(entries) if entries else "  (Empty directory)")
        except Exception as e:
            logger.error(f"[FilesystemPlugin] Error listing directory '{path}': {e}")
            return f"Failed to list directory: {e}"

    @dione_tool(
        description="Read the contents of a text file with optional line offset and limit",
        permission_level="read",
    )
    async def read_file(self, path: str, start_line: int = 1, max_lines: int = 150) -> str:
        """Read a text file's contents safely with encoding resilience.
        
        :param path: Path to the file to read
        :param start_line: 1-indexed starting line number (default: 1)
        :param max_lines: Maximum number of lines to return (default: 150)
        """
        target = Path(path).expanduser().resolve()

        if not target.exists():
            return f"File not found: {path}"
        if not target.is_file():
            return f"Not a file: {path}"

        try:
            # Resilient read with UTF-8 primary, fallback replacement
            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)

            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, start_idx + max_lines)
            selected = lines[start_idx:end_idx]

            header = f"=== File: {target.name} (Lines {start_idx + 1}-{end_idx} of {total_lines}) ===\n"
            body = "\n".join(f"{i + 1:4d} | {line}" for i, line in enumerate(selected, start=start_idx))

            footer = ""
            if end_idx < total_lines:
                footer = f"\n... ({total_lines - end_idx} more lines remaining)"

            return header + body + footer

        except Exception as e:
            return f"Failed to read file '{path}': {e}"

    @dione_tool(
        description="Write or append content to a file with system safety guardrails",
        requires_confirmation=True,
        permission_level="write",
    )
    async def write_file(self, path: str, content: str, append: bool = False) -> str:
        """Write or append text content to a file safely.
        
        :param path: Destination file path
        :param content: Content to write
        :param append: If true, append to existing file; otherwise overwrite
        """
        target = Path(path).expanduser().resolve()

        # Poset Lattice Path Safety check
        rejection = self._is_path_protected(target)
        if rejection:
            logger.warning(f"[FilesystemPlugin] Blocked write to protected path `{target}`: {rejection}")
            return f"SAFETY REFUSAL: Cannot write to '{path}'. Reason: {rejection}"

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"

            with open(target, mode, encoding="utf-8", errors="replace") as f:
                f.write(content)

            action = "Appended to" if append else "Successfully wrote"
            byte_count = len(content.encode("utf-8"))
            return f"{action} '{target.name}' ({byte_count} bytes written at {target})."
        except Exception as e:
            logger.error(f"[FilesystemPlugin] Error writing to '{path}': {e}")
            return f"Failed to write file '{path}': {e}"

    @dione_tool(
        description="Safely move a file or directory to the OS Recycle Bin (Soft Delete with Undo)",
        requires_confirmation=True,
        permission_level="privileged",
    )
    async def delete_file(self, path: str) -> str:
        """Safely delete a file or directory by moving it to the OS Recycle Bin.
        
        :param path: Path to the file or directory to recycle
        """
        target = Path(path).expanduser().resolve()

        if not target.exists():
            return f"Cannot delete: '{path}' does not exist."

        rejection = self._is_path_protected(target)
        if rejection:
            logger.warning(f"[FilesystemPlugin] Blocked delete of protected path `{target}`: {rejection}")
            return f"SAFETY REFUSAL: Cannot delete '{path}'. Reason: {rejection}"

        try:
            target_name = target.name
            success = self._recycle_path(target)
            if success:
                logger.info(f"[FilesystemPlugin] Recycled '{target}' into OS Recycle Bin.")
                return f"Successfully moved '{target_name}' to the Windows Recycle Bin (restorable)."
            else:
                return f"Failed to recycle '{target_name}': OS returned error code."
        except Exception as e:
            logger.error(f"[FilesystemPlugin] Delete error for '{path}': {e}")
            return f"Failed to delete '{path}': {e}"

    @dione_tool(
        description="Inspect metadata, permissions, and timestamps of a file or directory",
        permission_level="read",
    )
    async def get_file_info(self, path: str) -> str:
        """Get detailed metadata for a file or directory.
        
        :param path: Path to the target file or directory
        """
        try:
            target = Path(path).expanduser().resolve()
            if not target.exists():
                return f"Path does not exist: {path}"

            stat = target.stat()
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            is_dir = target.is_dir()
            size_bytes = stat.st_size

            if is_dir:
                size_str = "N/A (Directory)"
            elif size_bytes < 1024:
                size_str = f"{size_bytes} Bytes"
            elif size_bytes < 1024 * 1024:
                size_str = f"{round(size_bytes / 1024, 2)} KB"
            else:
                size_str = f"{round(size_bytes / (1024 * 1024), 2)} MB"

            report = [
                f"Path: {target}",
                f"Type: {'Directory' if is_dir else 'File'}",
                f"Size: {size_str}",
                f"Created: {created}",
                f"Last Modified: {modified}",
                f"Extension: {target.suffix or '(none)'}",
                f"Is Writable: {os.access(target, os.W_OK)}",
            ]
            return "File Metadata:\n" + "\n".join(f"  * {line}" for line in report)
        except Exception as e:
            return f"Failed to retrieve metadata for '{path}': {e}"

    @dione_tool(
        description="Search for files matching a pattern with folder pruning and depth control",
        permission_level="read",
    )
    async def search_files(
        self,
        directory: str = ".",
        pattern: str = "*",
        max_depth: int = 6,
        max_results: int = 50,
    ) -> str:
        """Search for files matching a pattern, pruning heavy vendor/build directories.
        
        :param directory: Starting directory for search (default: current directory)
        :param pattern: Glob pattern (e.g. '*.py', '*report*', '*.pdf')
        :param max_depth: Maximum directory recursion depth (default: 6)
        :param max_results: Maximum number of matches to return (default: 50)
        """
        try:
            start_path = Path(directory).expanduser().resolve()
            if not start_path.exists() or not start_path.is_dir():
                return f"Directory does not exist: {directory}"

            matches: List[str] = []
            start_time = time.time()
            start_depth = len(start_path.parts)

            for root, dirs, files in os.walk(start_path):
                # 10s execution timeout guardrail
                if time.time() - start_time > 10.0:
                    matches.append(f"... [Search paused: 10s timeout reached]")
                    break

                curr_path = Path(root)
                curr_depth = len(curr_path.parts) - start_depth
                if curr_depth >= max_depth:
                    dirs[:] = []
                    continue

                # Prune heavy / cache directories in-place
                dirs[:] = [
                    d for d in dirs
                    if d.lower() not in self.PRUNED_DIRECTORIES and not d.startswith(".")
                ]

                # Match files
                for f in files:
                    if fnmatch.fnmatch(f.lower(), pattern.lower()):
                        rel_path = os.path.relpath(os.path.join(root, f), start_path)
                        matches.append(rel_path)
                        if len(matches) >= max_results:
                            break

                if len(matches) >= max_results:
                    break

            if not matches:
                return f"No files matching '{pattern}' found in {start_path} (searched depth {max_depth})."

            header = f"Found {len(matches)} matches for '{pattern}' in {start_path}:"
            return header + "\n" + "\n".join(f"  * {m}" for m in matches)
        except Exception as e:
            logger.error(f"[FilesystemPlugin] Search error: {e}")
            return f"Error executing file search: {e}"
