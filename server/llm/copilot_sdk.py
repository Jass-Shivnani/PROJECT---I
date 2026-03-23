"""
Dione AI — GitHub Copilot SDK Backend

Uses the official GitHub Copilot SDK (github-copilot-sdk) to
communicate with GitHub Copilot via the Copilot CLI (JSON-RPC).

Authentication uses the logged-in GitHub user (same as VS Code).
No API key needed — just `copilot` CLI installed and GitHub signed in.

pip install github-copilot-sdk
"""

import asyncio
import time
from typing import AsyncGenerator, Optional
from loguru import logger

from server.llm.adapter import BaseLLMAdapter, LLMRequest, LLMResponse
from copilot import CopilotClient, PermissionHandler, SessionConfig


class CopilotAdapter(BaseLLMAdapter):
    """
    LLM adapter backed by the GitHub Copilot SDK.

    Uses `send_and_wait()` for reliable request/response,
    and event callbacks for streaming.
    """

    def __init__(self, model: str = "claude-sonnet-4.6"):
        self.model = model
        self._client: Optional[CopilotClient] = None
        self._initialized = False
        self._max_retries = 3
        logger.info(f"Copilot SDK adapter created: model={self.model}")

    async def _ensure_client(self):
        """Lazily start the CopilotClient (spawns the CLI server)."""
        if self._initialized and self._client:
            return

        self._client = CopilotClient({
            "auto_start": True,
            "auto_restart": True,
            "use_logged_in_user": True,
            "log_level": "warning",
        })
        await self._client.start()
        self._initialized = True
        logger.info("Copilot SDK client started (CLI JSON-RPC)")

    # ------------------------------------------------------------------
    # generate() — complete response via send_and_wait()
    # ------------------------------------------------------------------

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send messages and return a complete response."""
        await self._ensure_client()
        start = time.monotonic()

        # Separate system prompt from conversation
        system_content = ""
        conversation_parts = []
        for msg in request.messages:
            if msg.role == "system":
                system_content = msg.content
            elif msg.role == "user":
                conversation_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                conversation_parts.append(f"Assistant: {msg.content}")
            elif msg.role == "observation":
                conversation_parts.append(f"[Tool Result]: {msg.content}")

        conversation_text = "\n\n".join(conversation_parts)

        # Build prompt — embed system instructions inside the prompt
        # so the Copilot agent cannot override them.
        full_prompt = (
            f"<<MANDATORY INSTRUCTIONS — FOLLOW EXACTLY>>\n"
            f"{system_content}\n"
            f"<<END INSTRUCTIONS>>\n\n"
            f"{conversation_text}\n\n"
            f"Respond with ONLY a JSON object. No markdown, no extra text."
        )

        # Build session config
        session_config: SessionConfig = {
            "model": self.model,
            "on_permission_request": PermissionHandler.approve_all,
        }

        # Retry loop for transient session failures
        last_error = None
        for attempt in range(1, self._max_retries + 1):
            session = None
            try:
                session = await self._client.create_session(session_config)

                # Use send_and_wait for reliable request/response
                result = await session.send_and_wait(
                    {"prompt": full_prompt},
                    timeout=90.0,
                )

                if result is None:
                    raise RuntimeError("No response from Copilot SDK (timeout or empty)")

                # Extract content from the result
                content = ""
                if hasattr(result, "data") and hasattr(result.data, "content"):
                    content = result.data.content or ""

                if not content:
                    raise RuntimeError("Empty response content from Copilot SDK")

                latency = (time.monotonic() - start) * 1000

                # Extract token counts if available
                input_tokens = 0
                output_tokens = 0
                if hasattr(result, "data"):
                    input_tokens = getattr(result.data, "input_tokens", 0) or 0
                    output_tokens = getattr(result.data, "output_tokens", 0) or 0

                return LLMResponse(
                    content=content,
                    model=self.model,
                    prompt_tokens=input_tokens,
                    completion_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    finish_reason="stop",
                    latency_ms=latency,
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Copilot SDK attempt {attempt}/{self._max_retries} "
                    f"failed: {e}"
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(1.0 * attempt)
            finally:
                if session:
                    try:
                        await session.destroy()
                    except Exception:
                        pass

        latency = (time.monotonic() - start) * 1000
        logger.error(f"Copilot SDK all {self._max_retries} attempts failed: {last_error}")
        raise RuntimeError(f"Copilot SDK error after {self._max_retries} retries: {last_error}")

    # ------------------------------------------------------------------
    # stream() — token-by-token streaming via event callbacks
    # ------------------------------------------------------------------

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream tokens as they arrive."""
        await self._ensure_client()

        # Separate system message
        system_content = ""
        conversation_parts = []
        for msg in request.messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                conversation_parts.append(msg.content)

        full_prompt = "\n\n".join(conversation_parts)

        session_config: SessionConfig = {
            "model": self.model,
            "streaming": True,
            "on_permission_request": PermissionHandler.approve_all,
        }
        if system_content:
            session_config["system_message"] = {"content": system_content}

        session = await self._client.create_session(session_config)

        # Use a queue to bridge event callbacks → async generator
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()

        def on_event(event):
            etype = event.type.value if hasattr(event.type, "value") else str(event.type)
            if etype == "assistant.message_delta":
                delta = getattr(event.data, "delta_content", "") or ""
                if delta:
                    queue.put_nowait(delta)
            elif etype in ("session.idle", "assistant.message"):
                queue.put_nowait(SENTINEL)
            elif etype == "error":
                queue.put_nowait(SENTINEL)

        session.on(on_event)
        await session.send({"prompt": full_prompt})

        try:
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=60.0)
                if item is SENTINEL:
                    break
                yield item
        finally:
            try:
                await session.destroy()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Verify the Copilot CLI backend is reachable."""
        try:
            await self._ensure_client()
            return True
        except Exception as e:
            logger.error(f"Copilot SDK health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """List available models via Copilot CLI."""
        try:
            await self._ensure_client()
            models = await self._client.list_models()
            return [
                m.id if hasattr(m, "id") else str(m)
                for m in models
            ]
        except Exception:
            return [self.model]

    async def get_model_info(self) -> dict:
        """Get info about the current model."""
        return {
            "model": self.model,
            "provider": "github-copilot-sdk",
            "type": "cloud",
            "auth": "github-signed-in-user",
        }

    async def close(self):
        """Stop the Copilot CLI server."""
        if self._client:
            try:
                await self._client.stop()
            except Exception:
                pass
            self._client = None
            self._initialized = False
            logger.info("Copilot SDK client stopped")
