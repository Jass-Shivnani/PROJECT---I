"""
Dione AI — llama.cpp LLM Backend

Direct llama.cpp inference via the llama-cpp-python bindings.
This is the fallback when Ollama is not installed — it loads
GGUF model files directly.

No external server needed; the model runs in-process.
"""

import time
from typing import AsyncGenerator, Optional
from loguru import logger

from server.llm.adapter import BaseLLMAdapter, LLMRequest, LLMResponse


class LlamaCppAdapter(BaseLLMAdapter):
    """
    LLM adapter for llama-cpp-python (direct GGUF loading).

    Use this when you want maximum control over the model
    or when Ollama is not available. Requires a .gguf model file.
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
        n_threads: Optional[int] = None,
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        self._model = None
        logger.info(f"LlamaCpp adapter created: {model_path}")

    async def _load_model(self):
        """Lazy-load the model on first use."""
        if self._model is not None:
            return

        try:
            from llama_cpp import Llama

            logger.info(f"Loading GGUF model: {self.model_path}")
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                n_threads=self.n_threads,
                verbose=False,
            )
            logger.info("Model loaded successfully")
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python is not installed. "
                "Install it with: pip install llama-cpp-python"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")

    def _format_messages(self, messages) -> str:
        """
        Convert chat messages to a prompt string.
        Uses ChatML format (compatible with most models).
        """
        prompt = ""
        for msg in messages:
            if msg.role == "system":
                prompt += f"<|im_start|>system\n{msg.content}<|im_end|>\n"
            elif msg.role == "user":
                prompt += f"<|im_start|>user\n{msg.content}<|im_end|>\n"
            elif msg.role == "assistant":
                prompt += f"<|im_start|>assistant\n{msg.content}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"
        return prompt

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete response."""
        await self._load_model()
        start = time.monotonic()

        prompt = self._format_messages(request.messages)

        stop_sequences = request.stop or ["<|im_end|>"]

        result = self._model(
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=stop_sequences,
        )

        latency = (time.monotonic() - start) * 1000

        content = result["choices"][0]["text"]
        usage = result.get("usage", {})

        return LLMResponse(
            content=content.strip(),
            model=self.model_path.split("/")[-1].split("\\")[-1],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=result["choices"][0].get("finish_reason", "stop"),
            latency_ms=latency,
        )

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream tokens one at a time."""
        await self._load_model()

        prompt = self._format_messages(request.messages)
        stop_sequences = request.stop or ["<|im_end|>"]

        for chunk in self._model(
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=stop_sequences,
            stream=True,
        ):
            token = chunk["choices"][0]["text"]
            if token:
                yield token

    async def health_check(self) -> bool:
        """Check if the model can be loaded."""
        try:
            await self._load_model()
            return self._model is not None
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """Return the loaded model (only one at a time for llama.cpp)."""
        model_name = self.model_path.split("/")[-1].split("\\")[-1]
        return [model_name]

    async def get_model_info(self) -> dict:
        """Get info about the loaded model."""
        await self._load_model()
        model_name = self.model_path.split("/")[-1].split("\\")[-1]
        info = {
            "model": model_name,
            "path": self.model_path,
            "context_length": self.n_ctx,
            "gpu_layers": self.n_gpu_layers,
        }
        if self._model:
            info["vocab_size"] = self._model.n_vocab()
        return info

    async def close(self):
        """Unload the model."""
        if self._model:
            del self._model
            self._model = None
            logger.info("LlamaCpp model unloaded")
