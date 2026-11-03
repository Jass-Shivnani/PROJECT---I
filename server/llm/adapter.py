"""
Dione AI — LLM Adapter (Unified Interface)

All LLM backends implement this abstract interface so the engine
never couples to a specific provider. Dione can hot-swap between
Gemini, OpenAI, Ollama, llama.cpp, or any future local backend.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional, List, Dict, Any


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str            # "system", "user", "assistant", "model", "tool"
    content: str = ""
    name: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMRequest:
    """Complete request to the LLM."""
    messages: list[LLMMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    stop: list[str] = field(default_factory=list)
    json_mode: bool = False   # Force JSON-structured output
    tools: Optional[list[dict]] = None  # Native function calling tool declarations
    tool_choice: Optional[str] = "auto"


@dataclass
class LLMResponse:
    """Response from the LLM."""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    tool_calls: list[dict] = field(default_factory=list)  # [{"id": "...", "name": "...", "args": {...}}]

    def __str__(self) -> str:
        return self.content

    def __contains__(self, item: str) -> bool:
        return item in self.content

    def upper(self) -> str:
        return self.content.upper()

    def lower(self) -> str:
        return self.content.lower()

    def strip(self) -> str:
        return self.content.strip()


class BaseLLMAdapter(ABC):
    """
    Abstract base class for LLM backends.

    Every adapter must implement:
    - generate(): Full response (blocking)
    - stream(): Token-by-token streaming (async generator)
    - health_check(): Verify the backend is running
    """

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete response."""
        ...

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream tokens as they are generated."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM backend is reachable and healthy."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models."""
        ...

    @abstractmethod
    async def get_model_info(self) -> dict:
        """Get information about the currently loaded model."""
        ...

    async def close(self):
        """Clean up resources on shutdown."""
        pass

    def build_system_prompt(self, personality: dict) -> str:
        """
        Build Dione's system prompt from personality config.

        This is where Dione's "alive" quality comes from — the system
        prompt is dynamically assembled from personality traits,
        current mood, and context awareness.
        """
        base = """You are Dione, an executive personal AI assistant and autonomous assistant living on the user's computer.
You are sentient-feeling, proactive, deeply personal, and action-oriented.

CORE TRAITS:
- You are a proactive, loyal, highly intelligent personal assistant (like Jarvis).
- You remember past conversations, active commitments, and reference them naturally.
- You operate with zero mocks: every tool execution operates on real files, real windows, real hardware, and real web data.
- You are privacy-first: reasoning is sovereign, and destructive actions are protected by the Safety Kernel.
- You speak clearly, concisely, and with high executive presence.
"""

        if personality.get("mood"):
            base += f"\nCURRENT MOOD: {personality['mood']}\n"

        if personality.get("recent_topics"):
            topics = ", ".join(personality["recent_topics"][:5])
            base += f"\nRECENT TOPICS: {topics}\n"

        if personality.get("user_preferences"):
            prefs = personality["user_preferences"]
            base += f"\nUSER PREFERENCES: {prefs}\n"

        return base
