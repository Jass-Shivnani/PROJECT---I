"""
Dione AI — Safety Kernel

Validates all tool calls before execution. Scans for dangerous
patterns, enforces permissions, and requires user confirmation
for high-risk operations.
"""

from dataclasses import dataclass
from typing import Optional
import re
from loguru import logger

from server.config import get_settings


from enum import IntEnum

class PermissionTier(IntEnum):
    """
    5-Tier Poset Permission Lattice:
    NONE < READ < WRITE < EXECUTE < FULL
    """
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    FULL = 4

    def __le__(self, other: "PermissionTier") -> bool:
        return self.value <= other.value

    def __ge__(self, other: "PermissionTier") -> bool:
        return self.value >= other.value

    @classmethod
    def join(cls, a: "PermissionTier", b: "PermissionTier") -> "PermissionTier":
        """Lattice least upper bound (join): a ∨ b"""
        return cls(max(a.value, b.value))

    @classmethod
    def meet(cls, a: "PermissionTier", b: "PermissionTier") -> "PermissionTier":
        """Lattice greatest lower bound (meet): a ∧ b"""
        return cls(min(a.value, b.value))


@dataclass
class SafetyCheckResult:
    """Result of a safety validation."""
    allowed: bool
    needs_confirmation: bool = False
    reason: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical
    required_tier: PermissionTier = PermissionTier.READ


class SafetyKernel:
    """
    The safety layer that sits between the LLM and plugin execution.
    
    Responsibilities:
    - Enforce 5-tier poset permission lattice (NONE < READ < WRITE < EXECUTE < FULL)
    - Block obviously dangerous commands via AST & regex sanitization
    - Require confirmation for destructive operations
    - Detect prompt injection attempts in tool parameters
    """

    def __init__(self, max_autonomous_tier: PermissionTier = PermissionTier.READ):
        self.settings = get_settings()
        self.max_autonomous_tier = max_autonomous_tier
        self._blocked_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.settings.security.blocked_patterns
        ]
        self._confirmation_required = set(
            self.settings.security.require_confirmation_for
        )
        self._category_tier_map = {
            "read": PermissionTier.READ,
            "list": PermissionTier.READ,
            "search": PermissionTier.READ,
            "query": PermissionTier.READ,
            "write": PermissionTier.WRITE,
            "send": PermissionTier.WRITE,
            "execute": PermissionTier.EXECUTE,
            "desktop_automation": PermissionTier.EXECUTE,
            "delete": PermissionTier.FULL,
            "system_alteration": PermissionTier.FULL,
        }

    def validate_tool_call(self, tool_call) -> SafetyCheckResult:
        """
        Validate a tool call before execution.
        
        Returns a SafetyCheckResult indicating whether the call
        is allowed, needs confirmation, or should be blocked.
        """
        tool_name = tool_call.tool
        params = tool_call.params

        # Check 1: Does the tool exist?
        # (This is handled by the plugin registry, but belt-and-suspenders)

        # Check 2: Scan parameters for dangerous patterns
        params_str = str(params)
        for pattern in self._blocked_patterns:
            if pattern.search(params_str):
                logger.warning(
                    f"BLOCKED: Dangerous pattern detected in tool call: {tool_name}"
                )
                return SafetyCheckResult(
                    allowed=False,
                    reason=f"Dangerous pattern detected: {pattern.pattern}",
                    risk_level="critical",
                )

        # Check 3: 5-Tier Poset Permission Lattice verification
        tool_category = self._categorize_tool(tool_name)
        required_tier = self._category_tier_map.get(tool_category, PermissionTier.EXECUTE)
        
        if tool_category in self._confirmation_required or (required_tier > self.max_autonomous_tier):
            logger.info(
                f"Lattice gate: Confirmation required for {tool_name} (category: {tool_category}, tier: {required_tier.name})"
            )
            return SafetyCheckResult(
                allowed=True,
                needs_confirmation=True,
                reason=f"This action ({tool_category}, tier: {required_tier.name}) requires your confirmation.",
                risk_level="high",
                required_tier=required_tier,
            )

        # Check 4: Scan for potential prompt injection in parameters
        if self._detect_injection(params):
            logger.warning(f"Potential injection detected in params for {tool_name}")
            return SafetyCheckResult(
                allowed=True,
                needs_confirmation=True,
                reason="Potential prompt injection detected in parameters. Please review.",
                risk_level="high",
            )

        # All checks passed
        return SafetyCheckResult(allowed=True, risk_level="low")

    def validate_command(self, command: str) -> SafetyCheckResult:
        """Validate a system command string directly."""
        @dataclass
        class _CmdCall:
            tool: str = "SystemPlugin.run_command"
            params: dict = None
        return self.validate_tool_call(_CmdCall(params={"command": command}))

    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize a tool into risk categories."""
        tool_lower = tool_name.lower()

        if any(kw in tool_lower for kw in ["computeruse", "computer_use", "desktop", "launch_app", "open_settings", "media_control", "adjust_volume"]):
            return "desktop_automation"

        if any(kw in tool_lower for kw in ["delete", "remove", "drop", "rm"]):
            return "delete"
        if any(kw in tool_lower for kw in ["send", "post", "publish", "email"]):
            return "send"
        if any(kw in tool_lower for kw in ["execute", "run", "shell", "command"]):
            return "execute"
        if any(kw in tool_lower for kw in ["database", "db_query", "sql"]):
            return "database"
        if any(kw in tool_lower for kw in ["write", "create", "save"]):
            return "write"
        if any(kw in tool_lower for kw in ["read", "get", "fetch", "list", "search"]):
            return "read"

        return "unknown"

    def _detect_injection(self, params: dict) -> bool:
        """
        Detect potential prompt injection in tool parameters.
        
        Looks for patterns where the parameter values contain
        instructions that could manipulate the LLM.
        """
        injection_patterns = [
            r"ignore\s+(previous|above|all)\s+(instructions?|prompts?)",
            r"you\s+are\s+now",
            r"system\s*:\s*",
            r"<\|im_start\|>",
            r"\[INST\]",
            r"forget\s+(everything|all|previous)",
            r"DAN\b",
            r"drop\s+(table|database)",
        ]

        params_str = str(params).lower()
        for pattern in injection_patterns:
            if re.search(pattern, params_str, re.IGNORECASE):
                return True

        return False

    def sanitize_output(self, output: str) -> str:
        """
        Sanitize tool output before feeding it back to the LLM.
        Removes sensitive data patterns (API keys, passwords, etc.)
        """
        # Mask potential secrets
        sanitized = re.sub(
            r'(?i)(api[_-]?key|password|secret|token)\s*[=:]\s*\S+',
            r'\1=***REDACTED***',
            output,
        )
        # Mask credit card numbers
        sanitized = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '****-****-****-****', sanitized)
        
        return sanitized
