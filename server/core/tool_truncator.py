"""
Dione AI — Tool Result Truncator (Ported from OpenClaw's tool-result-truncation.ts)
==================================================================================
Prevents individual tool result outputs from consuming excessive context window tokens
or triggering Google GenAI 400 Bad Request payload overflow errors.

Heuristics:
- Max context share per tool result: ~30% or max 40,000 characters.
- Preserves head content with newline-aware cutoffs.
- Injects standard truncation notification informing the agent of partial view.
"""

from __future__ import annotations

import re
from typing import Optional
from loguru import logger

# Maximum characters allowed for a single tool result (conservative ~10k tokens)
MAX_TOOL_RESULT_CHARS = 40_000

# Minimum characters to preserve from the head of the output
MIN_KEEP_CHARS = 2_000

TRUNCATION_SUFFIX = (
    "\n\n⚠️ [Content truncated — original output was too large for the model's context window. "
    "The content above is a partial view. If you need more detail, request specific sections "
    "or use offset/limit parameters to read smaller chunks.]"
)


def truncate_tool_result_text(
    text: str,
    max_chars: int = MAX_TOOL_RESULT_CHARS,
    min_keep_chars: int = MIN_KEEP_CHARS,
    suffix: str = TRUNCATION_SUFFIX,
) -> str:
    """
    Truncate a single text string to fit within max_chars, preserving the beginning
    and breaking at a newline boundary if possible (ported from OpenClaw).
    """
    if not isinstance(text, str):
        text = str(text)

    if len(text) <= max_chars:
        return text

    keep_chars = max(min_keep_chars, max_chars - len(suffix))

    # Try to break at a newline boundary to avoid cutting mid-line
    cut_point = keep_chars
    last_newline = text.rfind("\n", 0, keep_chars)
    if last_newline > int(keep_chars * 0.8):
        cut_point = last_newline

    logger.debug(
        f"[ToolTruncation] Truncated output from {len(text)} chars to {cut_point} chars (limit {max_chars})"
    )
    return text[:cut_point] + suffix
