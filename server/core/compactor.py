"""
Dione AI — Session Compactor & Pre-Compaction Memory Flush
=========================================================
Ported directly from OpenClaw's compact.ts and memory-flush.ts:
1. Detects when session history approaches token/turn limits.
2. Triggers a silent pre-compaction turn reminding the agent to persist lasting notes to disk.
3. Recursively compresses older dialogue turns into a dense Markdown summary.
4. Prunes older turns while preserving recent turns and appending the summary block.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger


COMPACTION_PROMPT = """You are an expert executive context compactor.
Analyze the preceding conversation turns and generate a dense, structured summary preserving all critical information:
- Primary user goals and ongoing requests
- Empirical tool results, file changes, and system observations
- Explicit user preferences, facts, or decisions established
- Current unresolved state and immediate next steps

Format the summary as concise Markdown with bullet points. Avoid filler words. Be dense and precise."""

MEMORY_FLUSH_SYSTEM_PROMPT = "Session nearing compaction. Store durable memories now."
MEMORY_FLUSH_USER_PROMPT = (
    "Session nearing compaction. Write any lasting notes, user preferences, or architecture decisions "
    "to memory using `memory_write`; reply with ONLY 'NO_REPLY' if nothing needs to be stored."
)


class SessionCompactor:
    """Manages automated session compaction and pre-compaction memory persistence."""

    def __init__(
        self,
        max_turns_threshold: int = 24,
        compact_keep_recent: int = 4,
    ):
        self.max_turns_threshold = max_turns_threshold
        self.compact_keep_recent = compact_keep_recent

    def should_compact(self, history: List[Any]) -> bool:
        """Determines if the session has reached the compaction threshold."""
        return len(history) >= self.max_turns_threshold

    async def run_pre_compaction_memory_flush(
        self,
        client: Any,
        model_name: str,
        memory_plugin: Any,
        recent_context: str,
    ) -> bool:
        """
        Executes OpenClaw's silent pre-compaction turn.
        Gives the model an opportunity to write durable memories to disk before context is pruned.
        """
        logger.info("[Compactor] Initiating silent pre-compaction memory flush turn...")
        try:
            from google.genai import types

            callables = [memory_plugin.memory_write]
            config = types.GenerateContentConfig(
                tools=callables,
                temperature=0.2,
                system_instruction=MEMORY_FLUSH_SYSTEM_PROMPT,
            )

            prompt = f"Recent Context:\n{recent_context}\n\nInstruction:\n{MEMORY_FLUSH_USER_PROMPT}"
            resp = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

            # Check if function calls were made (model wrote to memory)
            if hasattr(resp, "function_calls") and resp.function_calls:
                for fc in resp.function_calls:
                    if fc.name == "memory_write":
                        args = dict(fc.args or {})
                        logger.info(f"[Compactor] Flush persisted memory: {args}")
                        await memory_plugin.memory_write(**args)

            logger.info("[Compactor] Pre-compaction memory flush complete.")
            return True
        except Exception as e:
            logger.warning(f"[Compactor] Pre-compaction memory flush failed: {e}")
            return False

    async def compact_history(
        self,
        client: Any,
        model_name: str,
        history: List[Dict[str, str]],
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Summarizes older dialogue turns and retains only the most recent turns.
        Returns: (compacted_summary_text, retained_recent_turns)
        """
        if len(history) <= self.compact_keep_recent:
            return "", history

        to_compact = history[: -self.compact_keep_recent]
        retained = history[-self.compact_keep_recent :]

        # Format turns to text
        transcript_lines = []
        for msg in to_compact:
            role = msg.get("role", "unknown").upper()
            content = str(msg.get("content", ""))
            transcript_lines.append(f"[{role}]: {content}")

        transcript_text = "\n\n".join(transcript_lines)

        logger.info(f"[Compactor] Compacting {len(to_compact)} turns into summary block...")
        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=COMPACTION_PROMPT,
            )
            prompt = f"Conversation History to Compact:\n\n{transcript_text}"
            resp = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

            summary = resp.text or "Previous context compacted."
            compacted_header = f"### [Compacted Previous Context]\n{summary.strip()}\n"
            logger.info(f"[Compactor] Compaction successful (summary length: {len(summary)})")
            return compacted_header, retained
        except Exception as e:
            logger.error(f"[Compactor] Compaction summarization failed: {e}")
            # Fallback simple concatenation
            fallback_header = f"### [Compacted Context — Raw Summary]\n{to_compact[0].get('content', '')[:300]}..."
            return fallback_header, retained
