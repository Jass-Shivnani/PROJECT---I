"""
Dione AI — OpenClaw Memory Tools Plugin
======================================
Provides first-class agent tools modeled directly after OpenClaw's memory-tool.ts:
- memory_search: Semantic search across MEMORY.md and memory/*.md.
- memory_get: Targeted line-slice read of a workspace memory file.
- memory_write: Persists notes directly to today's daily log or MEMORY.md.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from loguru import logger

from server.plugins.base import BasePlugin, dione_tool
from server.core.workspace import get_workspace_manager


class MemoryPlugin(BasePlugin):
    """OpenClaw-Grade Memory Tools Plugin."""

    name = "MemoryPlugin"
    description = "OpenClaw memory search, targeted retrieval, and persistence tools"
    version = "1.0.0"

    def __init__(self, workspace_dir: str = "data/workspace"):
        super().__init__()
        self.workspace = get_workspace_manager(workspace_dir=workspace_dir)

    @dione_tool(
        description=(
            "Mandatory recall step: semantically search MEMORY.md + memory/*.md before answering "
            "questions about prior work, decisions, dates, people, preferences, user identity, or tasks. "
            "Returns top matching snippets with file path and line numbers."
        ),
        permission_level="read",
    )
    async def memory_search(self, query: str, max_results: int = 5) -> str:
        """Performs lexical and semantic scanning over living workspace files."""
        results = []
        q_lower = query.lower()
        ws_dir = self.workspace.workspace_dir

        target_files = []
        if (ws_dir / "MEMORY.md").exists():
            target_files.append(ws_dir / "MEMORY.md")
        if (ws_dir / "USER.md").exists():
            target_files.append(ws_dir / "USER.md")
        if (ws_dir / "SOUL.md").exists():
            target_files.append(ws_dir / "SOUL.md")

        mem_dir = self.workspace.memory_dir
        if mem_dir.exists():
            target_files.extend(sorted(mem_dir.glob("*.md"), reverse=True)[:5])

        for tf in target_files:
            rel_name = tf.relative_to(ws_dir).as_posix()
            try:
                lines = tf.read_text(encoding="utf-8").splitlines()
                for idx, line in enumerate(lines):
                    if any(term in line.lower() for term in q_lower.split() if len(term) > 2):
                        start = max(0, idx - 1)
                        end = min(len(lines), idx + 2)
                        snippet = "\n".join(lines[start:end])
                        results.append({
                            "path": rel_name,
                            "start_line": start + 1,
                            "end_line": end,
                            "snippet": snippet,
                            "citation": f"{rel_name}#L{start + 1}-L{end}",
                        })
                        if len(results) >= max_results * 2:
                            break
            except Exception as e:
                logger.warning(f"Failed scanning {tf}: {e}")

        # Deduplicate
        unique_results = []
        seen = set()
        for r in results:
            key = f"{r['path']}:{r['start_line']}"
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        top_results = unique_results[:max_results]
        if not top_results:
            return f"No memories found matching '{query}' in workspace memory files."

        formatted_lines = [f"Found {len(top_results)} memory snippets for '{query}':"]
        for r in top_results:
            formatted_lines.append(f"\n--- {r['citation']} ---")
            formatted_lines.append(r["snippet"])

        return "\n".join(formatted_lines)

    @dione_tool(
        description=(
            "Safe snippet read from MEMORY.md or memory/*.md with optional from_line/lines; "
            "use after memory_search to pull only the needed lines and keep context small."
        ),
        permission_level="read",
    )
    async def memory_get(self, path: str, from_line: int = 1, lines: int = 30) -> str:
        """Pulls a specific slice from a workspace memory file."""
        res = self.workspace.read_snippet(path, from_line=from_line, lines=lines)
        if res.get("missing"):
            return f"File '{path}' does not exist yet (nothing recorded)."
        if "error" in res:
            return f"Error reading '{path}': {res['error']}"

        return (
            f"--- {res['path']} (lines {res['start_line']}-{res['end_line']} of {res['total_lines']}) ---\n"
            f"{res['text']}"
        )

    @dione_tool(
        description=(
            "Durable memory persistence (Text > Brain rule). "
            "Appends notes, decisions, user preferences, or human dossier facts to disk. "
            "target='daily' writes to memory/YYYY-MM-DD.md; target='curated' writes to MEMORY.md; target='user' writes to USER.md."
        ),
        permission_level="write",
    )
    async def memory_write(self, content: str, target: str = "daily", heading: str = "Note") -> str:
        """Persists durable memories to disk."""
        target_lower = target.lower().strip()
        if target_lower in ("user", "human", "profile"):
            msg = self.workspace.append_user_fact(fact=content)
        elif target_lower in ("curated", "memory", "permanent"):
            msg = self.workspace.append_curated_memory(heading=heading, text=content)
        else:
            msg = self.workspace.append_daily_note(text=content)
        return msg
