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


@dataclass
class SafetyCheckResult:
    """Result of a safety validation."""
    allowed: bool
    needs_confirmation: bool = False
    reason: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical


class SafetyKernel:
    """
    The safety layer that sits between the LLM and plugin execution.
    
    Responsibilities:
    - Block obviously dangerous commands
    - Require confirmation for destructive operations
    - Sanitize inputs before they reach plugins
    - Detect prompt injection attempts in tool parameters
    """

    def __init__(self):
        self.settings = get_settings()
        self._blocked_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.settings.security.blocked_patterns
        ]
        self._confirmation_required = set(
            self.settings.security.require_confirmation_for
        )

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

        # Check 3: Does this tool category require confirmation?
        tool_category = self._categorize_tool(tool_name)
        if tool_category in self._confirmation_required:
            logger.info(
                f"Confirmation required for {tool_name} (category: {tool_category})"
            )
            return SafetyCheckResult(
                allowed=True,
                needs_confirmation=True,
                reason=f"This action ({tool_category}) requires your confirmation.",
                risk_level="high",
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

    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize a tool into risk categories."""
        tool_lower = tool_name.lower()

        if any(kw in tool_lower for kw in ["delete", "remove", "drop", "rm"]):
            return "delete"
        if any(kw in tool_lower for kw in ["send", "post", "publish", "email"]):
            return "send"
        if any(kw in tool_lower for kw in ["execute", "run", "shell", "command"]):
            return "execute"
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
