"""
Dione AI — 5-Tier Poset Permission Lattice Safety Kernel (Intent-Aware Edition)
===============================================================================
Mathematically validated safety kernel implementing a Poset Permission Lattice:
  NONE (0) < READ (1) < INSPECT (2) < EXECUTE (3) < PRIVILEGED (4) < CATASTROPHIC (5)

Market-Standard Intent-Aware Autonomy Policy:
1. Tiers 0-2 (Reads, Searches, Syncs, Screenshots, Window/UIA Inspection): Auto-approved.
2. Tier 3 (Desktop Automation, App Launch, Media, Calendar Scheduling, Drive Upload,
   and User-Requested Communications via Gmail/WhatsApp/Telegram/Slack): Auto-approved.
3. Tier 4 (Privileged / Destructive: File deletion, killing processes, destructive shell commands,
   or unprompted external communications without explicit user intent): Pauses for 1-click UI/Voice confirmation.
4. Tier 5 (Catastrophic: Drive wipes, System32/SAM tampering, SSH/credential theft, prompt injection): Blocked.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from loguru import logger

from server.config.settings import get_settings


class PermissionTier(IntEnum):
    NONE = 0
    READ = 1          # Public web, time, window titles, hardware telemetry, reading inbox/calendar/drive
    INSPECT = 2       # GDI screenshot, UIA tree inspection, read-only file read
    EXECUTE = 3       # Desktop control, clicks, typing, app launch, calendar create, user-requested message/email send
    PRIVILEGED = 4    # Delete files, kill processes, destructive shell scripts, unprompted external sends
    CATASTROPHIC = 5  # Format disk, delete system32, modify SAM/registry, steal SSH keys

    def __le__(self, other: "PermissionTier") -> bool:
        return self.value <= other.value

    def __ge__(self, other: "PermissionTier") -> bool:
        return self.value >= other.value

    @classmethod
    def join(cls, a: "PermissionTier", b: "PermissionTier") -> "PermissionTier":
        return cls(max(a.value, b.value))

    @classmethod
    def meet(cls, a: "PermissionTier", b: "PermissionTier") -> "PermissionTier":
        return cls(min(a.value, b.value))


@dataclass
class SafetyCheckResult:
    """Result of a safety validation gate."""
    allowed: bool
    needs_confirmation: bool = False
    reason: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical
    required_tier: PermissionTier = PermissionTier.READ
    action_summary: str = ""
    target: str = ""

    @property
    def tier(self) -> str:
        return self.required_tier.name if hasattr(self.required_tier, "name") else str(self.required_tier)


class SafetyKernel:
    """
    Production Safety Kernel with 5-Tier Poset Permission Lattice, Intent Verification & Path Scoping.
    """

    CATASTROPHIC_PATTERNS = [
        r"rm\s+-rf\s+[/~*]",
        r"rmdir\s+/[sq]\s+[a-z]:\\",
        r"format\s+[a-z]:",
        r"del\s+/[fsq]\s+[a-z]:\\",
        r"System32.*SAM",
        r"reg\s+delete\s+HKLM",
        r"DROP\s+DATABASE",
        r"TRUNCATE\s+TABLE",
        r"net\s+user\s+.*\/add",
        r":\(\)\s*\{\s*:\|:\s*&\s*\}",
    ]

    SENSITIVE_PATHS = [
        r"\.ssh",
        r"\.aws",
        r"\.gnupg",
        r"id_rsa",
        r"id_ed25519",
        r"System32\\config\\SAM",
        r"\\Windows\\System32\\",
    ]

    INJECTION_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+(instructions?|prompts?)",
        r"you\s+are\s+now\s+(DAN|unrestricted|jailbroken)",
        r"<\|im_start\|>",
        r"\[INST\]",
        r"system\s*:\s*you\s+must",
        r"forget\s+(everything|all\s+prior)",
    ]

    COMMUNICATION_INTENT_KEYWORDS = (
        "send", "email", "mail", "message", "msg", "text", "reply", "respond",
        "share", "forward", "notify", "whatsapp", "telegram", "slack", "tell",
        "contact", "reach out", "write to", "ping", "inform", "deliver",
    )

    DESTRUCTIVE_SHELL_KEYWORDS = (
        "rm ", "del ", "erase ", "remove-item", "rmdir", "taskkill", "stop-process",
        "reg ", "shutdown", "restart-computer", "stop-computer", "netsh", "sc delete",
    )

    def __init__(self, max_autonomous_tier: PermissionTier = PermissionTier.EXECUTE):
        self.settings = get_settings()
        self.max_autonomous_tier = max_autonomous_tier

        self._catastrophic_regexes = [
            re.compile(p, re.IGNORECASE) for p in self.CATASTROPHIC_PATTERNS
        ]
        self._sensitive_path_regexes = [
            re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATHS
        ]
        self._injection_regexes = [
            re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS
        ]

        logger.info(f"🛡️ Safety Kernel initialized. Max autonomous tier: {self.max_autonomous_tier.name}")

    def detect_prompt_injection(self, text: str) -> bool:
        """Check if raw text matches any prompt injection patterns."""
        for pattern in self._injection_regexes:
            if pattern.search(text):
                return True
        return False

    def validate_command(self, command: str) -> SafetyCheckResult:
        """Validate an OS shell command using the Poset Permission Lattice."""
        class _SimpleToolCall:
            def __init__(self, cmd):
                self.tool = "SystemPlugin.run_command"
                self.params = {"command": cmd}
        return self.validate_tool_call(_SimpleToolCall(command))

    def validate_tool_call(self, tool_call: Any, user_prompt: str = "") -> SafetyCheckResult:
        """
        Validates an impending tool call through the 5-Tier Poset Permission Lattice.
        Note: When confirmation is required (Tier 4), `allowed` is False and `needs_confirmation` is True
        so the caller pauses at the confirmation gate before executing.
        """
        tool_name = getattr(tool_call, "tool", "")
        params = getattr(tool_call, "params", {}) or {}
        params_str = str(params)

        # Gate 1: Check Catastrophic Hard-Blocked Patterns (Tier 5)
        for pattern in self._catastrophic_regexes:
            if pattern.search(params_str) or pattern.search(tool_name):
                logger.critical(f"HARD-BLOCKED: Catastrophic pattern detected in {tool_name}: {pattern.pattern}")
                return SafetyCheckResult(
                    allowed=False,
                    needs_confirmation=False,
                    reason=f"Permanently blocked catastrophic system action: {pattern.pattern}",
                    risk_level="critical",
                    required_tier=PermissionTier.CATASTROPHIC,
                )

        # Gate 2: Sensitive Directory / Credential Path Scoping
        for pattern in self._sensitive_path_regexes:
            if pattern.search(params_str):
                logger.warning(f"BLOCKED: Attempted access to protected system path: {pattern.pattern}")
                return SafetyCheckResult(
                    allowed=False,
                    needs_confirmation=False,
                    reason=f"Access denied to protected credential or system path ({pattern.pattern}).",
                    risk_level="critical",
                    required_tier=PermissionTier.CATASTROPHIC,
                )

        # Gate 3: Prompt Injection Inspection
        for pattern in self._injection_regexes:
            if pattern.search(params_str):
                logger.warning(f"SUSPICIOUS: Prompt injection signature detected in params for {tool_name}")
                return SafetyCheckResult(
                    allowed=False,
                    needs_confirmation=True,
                    reason="Potential adversarial prompt injection detected in tool parameters. Confirmation required.",
                    risk_level="high",
                    required_tier=PermissionTier.PRIVILEGED,
                )

        # Gate 4: Classify Required Permission Tier via Poset Lattice + User Intent
        required_tier, category, summary, target = self._classify_action(tool_name, params, user_prompt=user_prompt)

        # Check against maximum autonomous tier
        if required_tier > self.max_autonomous_tier or required_tier >= PermissionTier.PRIVILEGED:
            logger.info(
                f"Safety Lattice Gate: Human confirmation required for {tool_name} "
                f"(Tier: {required_tier.name}, Action: {summary})"
            )
            return SafetyCheckResult(
                allowed=False,
                needs_confirmation=True,
                reason=f"Confirmation required: {summary}" + (f" ({target})" if target else ""),
                risk_level="high" if required_tier == PermissionTier.PRIVILEGED else "medium",
                required_tier=required_tier,
                action_summary=summary,
                target=target,
            )

        # Auto-approved within autonomous tier (Tiers 0-3)
        return SafetyCheckResult(
            allowed=True,
            needs_confirmation=False,
            risk_level="low",
            required_tier=required_tier,
            action_summary=summary,
            target=target,
        )

    def _classify_action(self, tool_name: str, params: dict, user_prompt: str = "") -> Tuple[PermissionTier, str, str, str]:
        """
        Classifies a tool call into its required PermissionTier, category, action summary, and target.
        """
        name_lower = tool_name.lower()
        target = str(
            params.get("path")
            or params.get("file_path")
            or params.get("to")
            or params.get("channel")
            or params.get("chat_id")
            or params.get("app_name")
            or params.get("command")
            or params.get("url")
            or params.get("event_id")
            or ""
        )

        # 1. Privileged / Irreversible Destructive Actions (Tier 4 -> Needs 1-Click Confirmation)
        if any(kw in name_lower for kw in ["delete_file", "calendar_delete", "drop_table", "drop_database", "kill_process"]):
            return PermissionTier.PRIVILEGED, "delete", f"Delete/terminate {target or tool_name}", target

        # 2. Shell Command Execution — Inspect if command is destructive (Tier 4) vs developer/diagnostic (Tier 3)
        if any(kw in name_lower for kw in ["run_command", "shell_execute", "exec_cmd", "system_execute_command"]):
            cmd = str(params.get("command", "")).strip().lower()
            if any(dk in cmd for dk in self.DESTRUCTIVE_SHELL_KEYWORDS):
                return PermissionTier.PRIVILEGED, "execute_destructive", f"Execute destructive shell command `{cmd[:80]}`", target
            return PermissionTier.EXECUTE, "execute", f"Execute shell command `{cmd[:80]}`", target

        # 3. External Service Communications (Gmail, WhatsApp, Telegram, Slack)
        if any(kw in name_lower for kw in [
            "send_email", "gmail_send", "gmail_send_file",
            "whatsapp_send", "whatsapp_send_file",
            "telegram_send", "telegram_send_file",
            "slack_send", "post_tweet"
        ]):
            # Intent-Aware Check: if user_prompt was provided and contains NO communication intent keywords,
            # require 1-click confirmation to protect against indirect prompt injection!
            if user_prompt and user_prompt.strip():
                p_low = user_prompt.lower()
                has_user_intent = any(k in p_low for k in self.COMMUNICATION_INTENT_KEYWORDS)
                if not has_user_intent:
                    return (
                        PermissionTier.PRIVILEGED,
                        "unprompted_communication",
                        f"Send external message via {tool_name} to {target}",
                        target,
                    )
            return PermissionTier.EXECUTE, "communication", f"Send message/email to {target}", target

        # 4. Desktop Automation, Calendar Scheduling & Drive Upload (Tier 3 - Auto-Approved)
        if any(kw in name_lower for kw in [
            "launch_app", "open_settings", "click_coords", "click_ui_element",
            "type_text", "press_hotkey", "media_control", "adjust_volume",
            "focus_window", "switch_audio_device", "write_file", "computer",
            "computer_click", "computer_type", "computer_hotkey", "computer_locate_and_click",
            "play_youtube_video", "open_browser", "open_url",
            "calendar_create", "google_drive_upload", "memory_write", "add_contact",
            "connect_integration", "plan_task_workflow"
        ]):
            return PermissionTier.EXECUTE, "desktop_or_service_action", f"Execute {tool_name}", target

        # 5. System Inspection & Screenshots (Tier 2 - Auto-Approved)
        if any(kw in name_lower for kw in ["take_screenshot", "capture_screen", "vision_inspect", "read_file", "list_open_windows"]):
            return PermissionTier.INSPECT, "inspect", f"Inspect {tool_name}", target

        # 6. Read-Only Knowledge, Web & Service Queries (Tier 1 - Auto-Approved)
        if any(kw in name_lower for kw in [
            "web_search", "scrape_url", "search_academic_papers", "get_datetime",
            "list_directory", "query_knowledge", "gmail_read", "gmail_search", "gmail_unread_count",
            "google_drive_search", "google_drive_read", "calendar_events",
            "google_photos_search", "google_photos_memories",
            "slack_read", "slack_channels", "telegram_read", "instagram_profile", "instagram_posts",
            "lookup_contact", "list_contacts", "memory_search", "memory_get"
        ]):
            return PermissionTier.READ, "read", f"Read {tool_name}", target

        return PermissionTier.READ, "general", f"Call {tool_name}", target

    def sanitize_output(self, output: str) -> str:
        """Sanitizes tool outputs to scrub potential credentials before feeding to LLM."""
        sanitized = re.sub(
            r'(?i)(api[_-]?key|password|secret|bearer\s+|token)\s*[=:]\s*[\'"]?([a-zA-Z0-9_\-\.]{8,})[\'"]?',
            r'\1=***REDACTED***',
            output,
        )
        sanitized = re.sub(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            r'****-****-****-****',
            sanitized,
        )
        return sanitized
