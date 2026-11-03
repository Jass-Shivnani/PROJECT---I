"""
Dione AI — Conversation Turn Sequence Validator (Ported from OpenClaw's turns.ts)
================================================================================
Gemini and Anthropic APIs enforce strict turn alternating constraints:
- Gemini: User -> Model -> User -> Model, or FunctionCall -> FunctionResponse -> Model.
- Consecutive messages from the same role (e.g. multiple user messages or multiple assistant messages)
  cause 400 Bad Request or malformed sequence rejections.

This module merges consecutive turns and validates turn integrity before payload submission.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from loguru import logger


def merge_consecutive_turns(
    messages: List[Dict[str, Any]],
    target_role: str,
    delimiter: str = "\n\n",
) -> List[Dict[str, Any]]:
    """
    Merges consecutive messages with the target role together.
    Ported directly from OpenClaw's validateTurnsWithConsecutiveMerge.
    """
    if not messages:
        return []

    result: List[Dict[str, Any]] = []

    for msg in messages:
        if not isinstance(msg, dict):
            result.append(msg)
            continue

        role = msg.get("role")
        if not role:
            result.append(msg)
            continue

        if result and result[-1].get("role") == target_role and role == target_role:
            prev = result[-1]
            prev_content = prev.get("content", "")
            curr_content = msg.get("content", "")
            
            # Merge contents
            if isinstance(prev_content, str) and isinstance(curr_content, str):
                merged = f"{prev_content}{delimiter}{curr_content}"
            elif isinstance(prev_content, list) and isinstance(curr_content, list):
                merged = prev_content + curr_content
            else:
                merged = f"{str(prev_content)}{delimiter}{str(curr_content)}"

            prev["content"] = merged
            
            # Merge tool calls if any
            if "tool_calls" in msg and msg["tool_calls"]:
                prev_tools = prev.get("tool_calls") or []
                prev["tool_calls"] = prev_tools + msg["tool_calls"]
                
            continue

        result.append(dict(msg))

    return result


def validate_gemini_turns(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validates and repairs turn sequences for Gemini API:
    - Merges consecutive assistant/model messages.
    - Merges consecutive user messages.
    - Ensures clean user-model dialogue flow.
    """
    # 1. Merge consecutive assistant turns
    step1 = merge_consecutive_turns(messages, target_role="assistant")
    step2 = merge_consecutive_turns(step1, target_role="model")
    
    # 2. Merge consecutive user turns
    step3 = merge_consecutive_turns(step2, target_role="user")
    
    return step3
