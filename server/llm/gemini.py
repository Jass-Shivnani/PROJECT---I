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

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        if request.json_mode:
            config.response_mime_type = "application/json"

        # Model candidates with automatic fallback
        candidates = [self.model, "gemini-3-flash-preview", "gemini-flash-latest", "gemini-3.8-flash", "gemini-3.5-flash-lite"]
        # Deduplicate preserving order
        candidates = list(dict.fromkeys(candidates))

        last_error = None
        for candidate in candidates:
            for attempt in range(1, 4):
                try:
                    response = self._client.models.generate_content(
                        model=candidate,
                        contents=contents,
                        config=config,
                    )
                    latency = (time.monotonic() - start) * 1000
                    content = response.text or ""
                    usage = response.usage_metadata
                    return LLMResponse(
                        content=content,
                        model=candidate,
                        prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
                        completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
                        total_tokens=getattr(usage, "total_token_count", 0) if usage else 0,
                        finish_reason="stop",
                        latency_ms=latency,
                    )
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    is_transient = any(code in err_str for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "DeadlineExceeded"])
                    if is_transient and attempt < 3:
                        wait = 5.0 * attempt
                        logger.warning(f"Gemini {candidate} transient error ({err_str[:80]}), retrying in {wait:.1f}s (attempt {attempt}/3)")
                        await asyncio.sleep(wait)
                        continue
                    else:
                        logger.warning(f"Gemini model {candidate} attempt {attempt} failed: {err_str[:120]}")
                        break  # Try next candidate model

        logger.error(f"All Gemini candidates failed. Last error: {last_error}")
        raise last_error

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream tokens from Gemini."""
        self._ensure_client()

        contents = self._build_contents(request.messages)

        system_instruction = None
        for msg in request.messages:
            if msg.role == "system":
                system_instruction = msg.content
                break

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        candidates = [self.model]
        if "gemini-3.8-flash" in self.model:
            candidates.append("gemini-3.5-flash")
        elif "gemini-3.5-flash" in self.model:
            candidates.append("gemini-3.8-flash")
        else:
            candidates.extend(["gemini-3.8-flash", "gemini-3.5-flash"])
        candidates = list(dict.fromkeys(candidates))

        last_error = None
        for candidate in candidates:
            try:
                response = self._client.models.generate_content_stream(
                    model=candidate,
                    contents=contents,
                    config=config,
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini streaming {candidate} failed: {e}. Trying fallback...")
                continue

        logger.error(f"Gemini streaming failed across all candidates: {last_error}")
        raise last_error

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

    async def generate_vision(self, prompt: str, image_bytes: bytes, json_mode: bool = False) -> str:
        """Generate response given an image and prompt using multimodal Gemini."""
        self._ensure_client()
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1024,
        )
        if json_mode:
            config.response_mime_type = "application/json"

        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png",
        )

        candidates = [self.model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        candidates = list(dict.fromkeys(candidates))

        last_error = None
        for candidate in candidates:
            try:
                response = self._client.models.generate_content(
                    model=candidate,
                    contents=[prompt, image_part],
                    config=config,
                )
                return response.text or ""
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini vision {candidate} failed: {e}. Trying fallback...")
                continue

        logger.error(f"Gemini vision failed across all candidates: {last_error}")
        raise last_error

    async def close(self):
        """No persistent connection to close."""
        pass
