"""
Dione AI — Context-Preserving Tool Result Truncator & Base64 Scrubber
=====================================================================
Prevents tool outputs (especially screenshots, HTML dumps, and directory trees)
from bloating the LLM context window or slowing down multi-step execution.

Key protections:
1. Automatically strips raw base64 image payloads (`screenshot_png_b64`, `screenshot_b64`, `data:image/...`)
   so binary strings never enter text conversation history.
2. Caps individual tool outputs at 6,000 characters (~1,500 tokens) with clean newline breaks.
"""

from __future__ import annotations

import re
from loguru import logger

MAX_TOOL_RESULT_CHARS = 6_000
MIN_KEEP_CHARS = 1_200

TRUNCATION_SUFFIX = (
    "\n\n[Output truncated to keep context fast and focused. "
    "Use targeted queries or offset/limit parameters if you need specific lines.]"
)

_BASE64_JSON_PATTERN = re.compile(
    r'"(?:screenshot_png_b64|screenshot_b64|image_b64|audio_base64|data)"\s*:\s*"[A-Za-z0-9+/=\r\n]{200,}"',
    re.DOTALL,
)
_DATA_URI_PATTERN = re.compile(
    r"data:image/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=\r\n]{200,}",
    re.DOTALL,
)


def scrub_base64_blobs(text: str) -> str:
    """Remove large inline base64 strings from tool outputs so they never bloat LLM context."""
    if not text or len(text) < 250:
        return text
    cleaned = _BASE64_JSON_PATTERN.sub('"screenshot_b64": "[CAPTURED_IN_UI_VISION_BUFFER]"', text)
    cleaned = _DATA_URI_PATTERN.sub("[IMAGE_DATA_URI_IN_VISION_BUFFER]", cleaned)
    return cleaned


def truncate_tool_result_text(
    text: str,
    max_chars: int = MAX_TOOL_RESULT_CHARS,
    min_keep_chars: int = MIN_KEEP_CHARS,
    suffix: str = TRUNCATION_SUFFIX,
) -> str:
    """Scrub base64 blobs and truncate tool output to fit cleanly within max_chars."""
    if not isinstance(text, str):
        text = str(text)

    text = scrub_base64_blobs(text)

    if len(text) <= max_chars:
        return text

    keep_chars = max(min_keep_chars, max_chars - len(suffix))
    cut_point = keep_chars
    last_newline = text.rfind("\n", 0, keep_chars)
    if last_newline > int(keep_chars * 0.75):
        cut_point = last_newline

    logger.debug(
        f"[ToolTruncation] Compacted tool output from {len(text)} chars to {cut_point} chars"
    )
    return text[:cut_point] + suffix
