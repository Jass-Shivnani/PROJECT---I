"""
Dione AI — Gemini LLM Backend

Connects to Google's Gemini API for inference.
Requires a GEMINI_API_KEY environment variable.

pip install google-generativeai
"""

import time
import asyncio
from typing import AsyncGenerator
from loguru import logger

from server.llm.adapter import BaseLLMAdapter, LLMRequest, LLMResponse


class GeminiAdapter(BaseLLMAdapter):
    """
    LLM adapter for Google Gemini API.

    Supports Gemini 2.0 Flash, Gemini 1.5 Pro, etc.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._initialized = False
        logger.info(f"Gemini adapter created: {self.model}")

    def _ensure_client(self):
        """Lazy-initialize the Gemini client."""
        if self._initialized:
            return

        try:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
            self._initialized = True
            logger.info(f"Gemini client initialized for model: {self.model}")
        except ImportError:
            raise RuntimeError(
                "google-genai is not installed. "
                "Install with: pip install google-genai"
            )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete response using Gemini."""
        self._ensure_client()
        start = time.monotonic()

        # Build contents from messages
        contents = self._build_contents(request.messages)

        # System instruction (if any)
        system_instruction = None
        for msg in request.messages:
            if msg.role == "system":
                system_instruction = msg.content
                break

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
            )
            if system_instruction:
                config.system_instruction = system_instruction
            if request.json_mode:
                config.response_mime_type = "application/json"

            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            latency = (time.monotonic() - start) * 1000

            content = response.text or ""
            usage = response.usage_metadata

            return LLMResponse(
                content=content,
                model=self.model,
                prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
                completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
                total_tokens=getattr(usage, "total_token_count", 0) if usage else 0,
                finish_reason="stop",
                latency_ms=latency,
            )
        except Exception as e:
            error_str = str(e)
            # Retry on rate limit (429) with exponential backoff
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                for attempt in range(1, 4):  # 3 retries
                    wait = 2 ** attempt  # 2, 4, 8 seconds
                    logger.warning(f"Gemini rate limited, retrying in {wait}s (attempt {attempt}/3)")
                    await asyncio.sleep(wait)
                    try:
                        response = self._client.models.generate_content(
                            model=self.model,
                            contents=contents,
                            config=config,
                        )
                        latency = (time.monotonic() - start) * 1000
                        content = response.text or ""
                        usage = response.usage_metadata
                        return LLMResponse(
                            content=content,
                            model=self.model,
                            prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
                            completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
                            total_tokens=getattr(usage, "total_token_count", 0) if usage else 0,
                            finish_reason="stop",
                            latency_ms=latency,
                        )
                    except Exception:
                        if attempt == 3:
                            break
                        continue
            logger.error(f"Gemini generation error: {e}")
            raise

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream tokens from Gemini."""
        self._ensure_client()

        contents = self._build_contents(request.messages)

        system_instruction = None
        for msg in request.messages:
            if msg.role == "system":
                system_instruction = msg.content
                break

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = self._client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise

    def _build_contents(self, messages) -> list:
        """Convert LLMMessages to Gemini content format."""
        contents = []
        for msg in messages:
            if msg.role == "system":
                continue  # Handled via system_instruction
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})
        return contents

    async def health_check(self) -> bool:
        """Check if Gemini API is reachable."""
        try:
            self._ensure_client()
            # Quick test with minimal prompt
            from google.genai import types
            response = self._client.models.generate_content(
                model=self.model,
                contents="Say hi",
                config=types.GenerateContentConfig(max_output_tokens=5),
            )
            return response.text is not None
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """List available Gemini models."""
        try:
            self._ensure_client()
            models = self._client.models.list()
            return [m.name for m in models if "gemini" in m.name.lower()]
        except Exception:
            return [self.model]

    async def get_model_info(self) -> dict:
        """Get info about the current model."""
        return {
            "model": self.model,
            "provider": "google-gemini",
            "type": "cloud",
        }

    async def close(self):
        """No persistent connection to close."""
        pass
