"""
Dione AI — Context Manager

The "Hippocampus" of Dione. Manages the sliding context window,
retrieves relevant memories from the vector store, and ensures
the LLM never exceeds its token limit.
"""

from typing import Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class ContextWindow:
    """Represents the current context window state."""
    messages: list[dict]
    total_tokens: int
    max_tokens: int
    has_been_summarized: bool = False


class ContextManager:
    """
    Manages context for the LLM, including:
    - Sliding window to keep under token limits
    - RAG retrieval from vector store
    - Knowledge graph context injection
    - Conversation summarization
    """

    def __init__(self, max_context_tokens: int = 4096):
        self.max_context_tokens = max_context_tokens
        self._token_counter = None

    async def initialize(self):
        """Initialize token counter (lazy load tiktoken)."""
        try:
            import tiktoken
            self._token_counter = tiktoken.get_encoding("cl100k_base")
            logger.info("Token counter initialized (tiktoken)")
        except ImportError:
            logger.warning("tiktoken not available, using approximate counting")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        if self._token_counter:
            return len(self._token_counter.encode(text))
        # Approximate: ~4 chars per token
        return len(text) // 4

    def build_context(
        self,
        system_prompt: str,
        conversation_history: list[dict],
        rag_context: Optional[str] = None,
        knowledge_context: Optional[str] = None,
        sentiment_context: Optional[str] = None,
    ) -> list[dict]:
        """
        Build a context-aware message list that fits within token limits.
        
        Priority order (most important first):
        1. System prompt (always included)
        2. Latest user message (always included)
        3. Recent tool observations
        4. RAG context
        5. Knowledge graph context
        6. Older conversation turns (summarized if needed)
        """
        messages = [{"role": "system", "content": system_prompt}]
        remaining_tokens = self.max_context_tokens - self.count_tokens(system_prompt)

        # Always include the latest user message
        if conversation_history:
            latest = conversation_history[-1]
            remaining_tokens -= self.count_tokens(latest.get("content", ""))

        # Add contextual information
        if rag_context:
            rag_tokens = self.count_tokens(rag_context)
            if rag_tokens < remaining_tokens * 0.3:  # Max 30% for RAG
                messages.append({
                    "role": "system",
                    "content": f"[Relevant memories]: {rag_context}",
                })
                remaining_tokens -= rag_tokens

        if knowledge_context:
            kg_tokens = self.count_tokens(knowledge_context)
            if kg_tokens < remaining_tokens * 0.2:  # Max 20% for KG
                messages.append({
                    "role": "system",
                    "content": f"[Knowledge context]: {knowledge_context}",
                })
                remaining_tokens -= kg_tokens

        # Add conversation history (most recent first, until we run out of tokens)
        history_to_add = []
        for msg in reversed(conversation_history[:-1]):  # Exclude latest (added at end)
            msg_tokens = self.count_tokens(msg.get("content", ""))
            if msg_tokens <= remaining_tokens:
                history_to_add.insert(0, msg)
                remaining_tokens -= msg_tokens
            else:
                break

        messages.extend(history_to_add)

        # Add the latest message
        if conversation_history:
            messages.append(conversation_history[-1])

        return messages

    async def summarize_old_turns(
        self, messages: list[dict], llm_adapter
    ) -> str:
        """
        Summarize older conversation turns to free up context space.
        Uses the LLM itself to create the summary.
        """
        turns_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        
        summary_prompt = [
            {
                "role": "system",
                "content": "Summarize the following conversation turns concisely, preserving key facts, decisions, and tool results. Output only the summary.",
            },
            {"role": "user", "content": turns_text},
        ]

        summary = await llm_adapter.generate(summary_prompt)
        logger.debug(f"Summarized {len(messages)} turns into {self.count_tokens(summary)} tokens")
        return summary
