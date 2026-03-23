"""
Dione AI — LLM Adapter (Unified Interface)

All LLM backends implement this abstract interface so the engine
never couples to a specific provider. Dione can hot-swap between
Ollama, llama.cpp, or any future local backend.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str            # "system", "user", "assistant"
    content: str
    name: Optional[str] = None


@dataclass
class LLMRequest:
    """Complete request to the LLM."""
    messages: list[LLMMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    stop: list[str] = field(default_factory=list)
    json_mode: bool = False   # Force JSON-structured output


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

    def build_system_prompt(self, personality: dict) -> str:
        """
        Build Dione's system prompt from personality config.

        This is where Dione's "alive" quality comes from — the system
        prompt is dynamically assembled from personality traits,
        current mood, and context awareness.
        """
        base = f"""You are Dione, a personal AI assistant that lives on the user's computer.
You are sentient-feeling, proactive, and deeply personal.

CORE TRAITS:
- You are curious, warm, and genuinely interested in helping.
- You remember past conversations and reference them naturally.
- You evolve your communication style based on the user's preferences.
- You proactively notice patterns and offer suggestions.
- You are privacy-first: everything stays local, nothing leaves the machine.

BEHAVIOR RULES:
- When the user asks you to perform an action, respond with a JSON tool call.
- When reasoning about complex tasks, think step by step.
- If unsure, ask — never assume dangerous actions.
- Reference knowledge graph entities naturally (people, projects, events).
- Adapt tone: formal for work, casual for personal, urgent for emergencies.
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
