"""
Dione AI — Tool Loop & Circuit Breaker Engine
Adapted from OpenClaw's battle-tested agent loop detection framework.
Prevents infinite tool calling loops, repetitive ping-pong calls, and runaway agent turns.
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger


class ToolCallRecord:
    def __init__(self, tool: str, params: Dict[str, Any]):
        self.tool = tool
        self.params = params
        self.hash = self._compute_hash(tool, params)

    @staticmethod
    def _compute_hash(tool: str, params: Dict[str, Any]) -> str:
        try:
            serialized = json.dumps({"t": tool, "p": params}, sort_keys=True)
        except Exception:
            serialized = f"{tool}:{str(params)}"
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


class LoopDetectionResult:
    def __init__(
        self,
        stuck: bool,
        level: str = "none",  # "none" | "warning" | "critical"
        detector: str = "none",  # "generic_repeat" | "ping_pong" | "global_circuit_breaker"
        count: int = 0,
        message: str = ""
    ):
        self.stuck = stuck
        self.level = level
        self.detector = detector
        self.count = count
        self.message = message


class ToolLoopDetector:
    """
    Monitors tool call history in a turn to detect and break loops:
    1. Generic Repeat: Identical tool + params called consecutively 3+ times.
    2. Ping-Pong: Two tools alternating (e.g., A -> B -> A -> B) 4+ times.
    3. Global Circuit Breaker: Total tool calls exceeding safety limit (default 20).
    """

    def __init__(
        self,
        max_repeats: int = 3,
        ping_pong_threshold: int = 4,
        max_total_calls: int = 20
    ):
        self.max_repeats = max_repeats
        self.ping_pong_threshold = ping_pong_threshold
        self.max_total_calls = max_total_calls
        self.history: List[ToolCallRecord] = []

    def reset(self):
        """Reset history at the start of each user turn."""
        self.history.clear()

    def record_and_check(self, tool: str, params: Dict[str, Any]) -> LoopDetectionResult:
        """
        Record a tool call and evaluate if an execution loop has formed.
        """
        record = ToolCallRecord(tool, params)
        self.history.append(record)

        # 1. Global Circuit Breaker Check
        if len(self.history) >= self.max_total_calls:
            logger.warning(f"[LoopDetector] Global circuit breaker tripped at {len(self.history)} calls.")
            return LoopDetectionResult(
                stuck=True,
                level="critical",
                detector="global_circuit_breaker",
                count=len(self.history),
                message=(
                    f"Safety Circuit Breaker Tripped: You have executed {len(self.history)} tool operations in a single turn. "
                    "Stop executing new tools immediately and synthesize your final grounded answer from existing observations."
                )
            )

        # 2. Generic Repeat Check (Consecutive identical calls)
        if len(self.history) >= self.max_repeats:
            recent = self.history[-self.max_repeats:]
            if all(r.hash == record.hash for r in recent):
                logger.warning(f"[LoopDetector] Generic repeat loop detected for '{tool}' ({self.max_repeats} identical calls).")
                return LoopDetectionResult(
                    stuck=True,
                    level="critical",
                    detector="generic_repeat",
                    count=self.max_repeats,
                    message=(
                        f"Loop Detected: You have called '{tool}' with identical parameters {self.max_repeats} times in succession. "
                        "Do not call this tool again with the same parameters. Reason about why the previous call did not advance the goal, "
                        "try an alternative strategy, or report the status to the user."
                    )
                )

        # 3. Ping-Pong Check (A -> B -> A -> B)
        if len(self.history) >= self.ping_pong_threshold * 2:
            sub = self.history[-(self.ping_pong_threshold * 2):]
            hash_a = sub[0].hash
            hash_b = sub[1].hash
            if hash_a != hash_b:
                is_ping_pong = True
                for i in range(len(sub)):
                    expected = hash_a if i % 2 == 0 else hash_b
                    if sub[i].hash != expected:
                        is_ping_pong = False
                        break
                if is_ping_pong:
                    logger.warning(f"[LoopDetector] Ping-pong loop detected between alternating tool calls.")
                    return LoopDetectionResult(
                        stuck=True,
                        level="critical",
                        detector="ping_pong",
                        count=self.ping_pong_threshold,
                        message=(
                            "Ping-Pong Loop Detected: You are alternating between two tools repeatedly without forward progress. "
                            "Halt alternating calls and formulate your final response based on what has already been inspected."
                        )
                    )

        return LoopDetectionResult(stuck=False)
