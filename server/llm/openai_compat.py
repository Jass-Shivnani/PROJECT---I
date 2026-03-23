"""
Dione AI — OpenAI-Compatible LLM Backend

Works with any OpenAI-compatible API:
- OpenAI (GPT-4, GPT-3.5)
- GitHub Copilot / GitHub Models
- Azure OpenAI
- Local servers (LM Studio, text-generation-webui, etc.)

Just set the base_url and api_key.

pip install openai
"""

import time
from typing import AsyncGenerator
from loguru import logger

from server.llm.adapter import BaseLLMAdapter, LLMRequest, LLMResponse


class OpenAIAdapter(BaseLLMAdapter):
    """
    LLM adapter for OpenAI-compatible APIs.

    Supports any server implementing the OpenAI chat completions endpoint.
    This includes GitHub Models, Azure OpenAI, LM Studio, etc.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None
        self._async_client = None
        logger.info(f"OpenAI adapter created: {self.model} @ {self.base_url}")

    def _ensure_client(self):
        """Lazy-initialize the OpenAI client."""
        if self._async_client is not None:
            return

        try:
            from openai import AsyncOpenAI

            self._async_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info("OpenAI async client initialized")
        except ImportError:
            raise RuntimeError(
                "openai is not installed. Install with: pip install openai"
            )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete response."""
        self._ensure_client()
        start = time.monotonic()

        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.stop:
            kwargs["stop"] = request.stop
        if request.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._async_client.chat.completions.create(**kwargs)
            latency = (time.monotonic() - start) * 1000

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                finish_reason=choice.finish_reason or "stop",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream tokens from the API."""
        self._ensure_client()

        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        if request.stop:
            kwargs["stop"] = request.stop

        try:
            stream = await self._async_client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if the API is reachable."""
        try:
            self._ensure_client()
            response = await self._async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            return response.choices[0].message.content is not None
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """List available models."""
        try:
            self._ensure_client()
            models = await self._async_client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return [self.model]

    async def get_model_info(self) -> dict:
        """Get info about the current model."""
        return {
            "model": self.model,
            "provider": "openai-compatible",
            "base_url": self.base_url,
            "type": "cloud",
        }

    async def close(self):
        """Close the async client."""
        if self._async_client:
            await self._async_client.close()
