"""
Dione AI — Workspace Context Loader (Modeled directly after OpenClaw's workspace architecture)
=============================================================================================
Dynamically resolves and injects living workspace files into the agent system context:
- SOUL.md (Tone, demeanor, non-sycophantic boundaries)
- USER.md (Human dossier, preferences, timezone, projects)
- IDENTITY.md (Agent definition, creature, signature)
- AGENTS.md (Operating protocol: Text > Brain rule)
- MEMORY.md (Curated long-term memory)
- memory/YYYY-MM-DD.md (Today's and yesterday's running daily notes)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class WorkspaceManager:
    """Manages the living workspace directory and dynamic prompt context injection."""

    def __init__(self, workspace_dir: str = "data/workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.memory_dir = self.workspace_dir / "memory"
        self._ensure_structure()

    def _ensure_structure(self):
        """Ensures the workspace directories exist."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def load_project_context(self) -> str:
        """
        Builds the '# Project Context' block modeled directly after OpenClaw's buildAgentSystemPrompt.
        Reads SOUL.md, USER.md, IDENTITY.md, AGENTS.md, MEMORY.md, and daily logs.
        """
        files_to_load = [
            ("SOUL.md", self.workspace_dir / "SOUL.md"),
            ("USER.md", self.workspace_dir / "USER.md"),
            ("IDENTITY.md", self.workspace_dir / "IDENTITY.md"),
            ("AGENTS.md", self.workspace_dir / "AGENTS.md"),
            ("MEMORY.md", self.workspace_dir / "MEMORY.md"),
        ]

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        today_path = self.memory_dir / f"{today_str}.md"
        yesterday_path = self.memory_dir / f"{yesterday_str}.md"

        if yesterday_path.exists():
            files_to_load.append((f"memory/{yesterday_str}.md", yesterday_path))
        if today_path.exists():
            files_to_load.append((f"memory/{today_str}.md", today_path))

        lines: List[str] = [
            "# Project Context",
            "",
            "The following living workspace files have been loaded:",
            "If SOUL.md is present, embody its persona and tone. Avoid stiff, generic replies; follow its guidance unless higher-priority instructions override it.",
            "",
        ]

        for display_name, file_path in files_to_load:
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8").strip()
                    if content:
                        lines.append(f"## {display_name}")
                        lines.append("")
                        lines.append(content)
                        lines.append("")
                except Exception as err:
                    logger.warning(f"Failed to read workspace file {file_path}: {err}")

        return "\n".join(lines)

    def append_daily_note(self, text: str) -> str:
        """Appends a timestamped note to today's daily log file."""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        today_path = self.memory_dir / f"{today_str}.md"

        entry = f"\n- {time_str} - {text.strip()}\n"
        if not today_path.exists():
            today_path.write_text(f"# Daily Log - {today_str}\n{entry}", encoding="utf-8")
        else:
            with open(today_path, "a", encoding="utf-8") as f:
                f.write(entry)

        logger.info(f"[Workspace] Appended daily note to {today_path.name}")
        return f"Appended to memory/{today_str}.md: {text.strip()}"

    def append_curated_memory(self, heading: str, text: str) -> str:
        """Appends a significant durable milestone or preference to MEMORY.md."""
        memory_path = self.workspace_dir / "MEMORY.md"
        entry = f"\n### {heading.strip()}\n{text.strip()}\n"

        if not memory_path.exists():
            memory_path.write_text(f"# MEMORY.md - Curated Long-Term Memory\n{entry}", encoding="utf-8")
        else:
            with open(memory_path, "a", encoding="utf-8") as f:
                f.write(entry)

        logger.info(f"[Workspace] Appended curated memory under '{heading}' to MEMORY.md")
        return f"Appended durable memory under '{heading}' to MEMORY.md"

    def append_user_fact(self, fact: str) -> str:
        """Appends a learned user preference or personal fact to USER.md."""
        user_path = self.workspace_dir / "USER.md"
        entry = f"- {fact.strip()}\n"

        if not user_path.exists():
            user_path.write_text(
                f"# USER.md - About Your Human\n\n- **Name:** Jass Shivnani\n\n## Learned Facts & Preferences\n{entry}",
                encoding="utf-8",
            )
        else:
            content = user_path.read_text(encoding="utf-8")
            if "## Learned Facts & Preferences" not in content:
                content += f"\n\n## Learned Facts & Preferences\n{entry}"
            else:
                content += f"{entry}"
            user_path.write_text(content, encoding="utf-8")

        logger.info(f"[Workspace] Appended user fact to USER.md: {fact.strip()}")
        return f"Appended fact to USER.md: {fact.strip()}"

    def read_snippet(self, rel_path: str, from_line: Optional[int] = None, lines: Optional[int] = None) -> Dict[str, Any]:
        """
        Reads a specific slice of a workspace file (OpenClaw memory_get implementation).
        Degrades gracefully when a file does not exist.
        """
        file_path = self.workspace_dir / rel_path
        if not file_path.exists():
            return {"path": rel_path, "text": "", "disabled": False, "missing": True}

        try:
            full_text = file_path.read_text(encoding="utf-8")
            all_lines = full_text.splitlines()

            start = max(0, (from_line or 1) - 1)
            count = lines if lines is not None else len(all_lines)
            selected = all_lines[start : start + count]

            return {
                "path": rel_path,
                "text": "\n".join(selected),
                "total_lines": len(all_lines),
                "start_line": start + 1,
                "end_line": start + len(selected),
            }
        except Exception as e:
            return {"path": rel_path, "text": "", "error": str(e)}


# Global singleton instance
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager(workspace_dir: str = "data/workspace") -> WorkspaceManager:
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager(workspace_dir=workspace_dir)
    return _workspace_manager
