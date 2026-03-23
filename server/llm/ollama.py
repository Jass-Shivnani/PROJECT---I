"""
Dione AI — Ollama LLM Backend

Connects to a locally running Ollama server for inference.
Ollama handles model management, quantization, and GPU offloading.

Requires: `ollama serve` running on localhost:11434
"""

import time
from typing import AsyncGenerator
import httpx
from loguru import logger

from server.llm.adapter import BaseLLMAdapter, LLMRequest, LLMResponse


class OllamaAdapter(BaseLLMAdapter):
    """
    LLM adapter for Ollama (https://ollama.ai).

    Ollama provides a simple REST API for local model inference.
    It manages model downloads, quantization (GGUF), and GPU layers.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        logger.info(f"Ollama adapter initialized: {self.base_url} / {self.model}")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete response using Ollama's /api/chat endpoint."""
        start = time.monotonic()

        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        if request.stop:
            payload["options"]["stop"] = request.stop

        if request.json_mode:
            payload["format"] = "json"

        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            latency = (time.monotonic() - start) * 1000

            return LLMResponse(
                content=data["message"]["content"],
                model=data.get("model", self.model),
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                finish_reason="stop",
                latency_ms=latency,
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} — {e.response.text}")
            raise
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama. Is `ollama serve` running?")
            raise RuntimeError(
                "Ollama is not running. Start it with: ollama serve"
            )

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream tokens from Ollama's /api/chat endpoint."""
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        if request.stop:
            payload["options"]["stop"] = request.stop

        if request.json_mode:
            payload["format"] = "json"

        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        import json
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            token = chunk["message"]["content"]
                            if token:
                                yield token
                        if chunk.get("done", False):
                            return
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama for streaming.")
            raise RuntimeError("Ollama is not running. Start it with: ollama serve")

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List models available in Ollama."""
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def get_model_info(self) -> dict:
        """Get info about the currently loaded model."""
        try:
            response = await self._client.post(
                "/api/show", json={"name": self.model}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {"model": self.model, "error": str(e)}

    async def pull_model(self, model_name: str) -> bool:
        """Pull/download a model via Ollama."""
        logger.info(f"Pulling model: {model_name}")
        try:
            response = await self._client.post(
                "/api/pull",
                json={"name": model_name, "stream": False},
                timeout=httpx.Timeout(600.0),  # Models can be large
            )
            response.raise_for_status()
            logger.info(f"Model {model_name} pulled successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
