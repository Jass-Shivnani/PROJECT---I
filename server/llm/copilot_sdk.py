"""
Dione AI — GitHub Copilot SDK Backend

Uses the official GitHub Copilot CLI to generate responses.
Instead of using the buggy CopilotClient (which hangs indefinitely when the CLI 
demands interactive TOS approval for new models), we use `subprocess` directly 
so we can intercept errors and present them to the user instantly.
"""

import asyncio
import os
import re
import time
from typing import AsyncGenerator
from loguru import logger

from server.llm.adapter import BaseLLMAdapter, LLMRequest, LLMResponse

class CopilotAdapter(BaseLLMAdapter):
    """
    LLM adapter backed by the GitHub Copilot SDK CLI executable.

    Instead of using the buggy `CopilotClient` (which hangs when the CLI requires
    TOS approval for a new model), we invoke `copilot.exe -p` directly via subprocess.
    """

    def __init__(self, model: str = "gpt-5-mini", **kwargs):
        self.model = self._normalize_model(model)
        self._cli_path = None
        self._timeout_seconds = float(os.getenv("DIONE_COPILOT_TIMEOUT", "180"))
        logger.info(f"Copilot Subprocess adapter created: model={self.model}")

    def _normalize_model(self, model: str) -> str:
        aliases = {
            "gpt-4.1-mini": "gpt-4.1",
        }
        normalized = aliases.get(model, model)
        if normalized != model:
            logger.warning(f"Copilot model '{model}' is deprecated; using '{normalized}' instead")
        return normalized

    def _extract_allowed_models(self, stderr_str: str) -> list[str]:
        if "Allowed choices are" not in stderr_str:
            return []
        choices_part = stderr_str.split("Allowed choices are", 1)[1].strip().rstrip(".")
        return [m.strip() for m in choices_part.split(",") if m.strip()]

    async def _run_cli(self, cli_path: str, prompt: str, model: str):
        process = await asyncio.create_subprocess_exec(
            cli_path, "-p", prompt, "--model", model,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self._timeout_seconds)
        return process.returncode, stdout.decode().strip(), stderr.decode().strip()

    def _ensure_cli(self) -> str:
        """Find the bundled copilot CLI executable."""
        if self._cli_path:
            return self._cli_path

        try:
            from copilot.client import _get_bundled_cli_path
            self._cli_path = _get_bundled_cli_path()
            return self._cli_path
        except ImportError:
            raise RuntimeError(
                "github-copilot-sdk is not installed. "
                "Install with: pip install github-copilot-sdk"
            )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send messages to Copilot via subprocess."""
        try:
            cli_path = self._ensure_cli()
        except RuntimeError as e:
            return LLMResponse(content=f"System Error: {e}", model=self.model)

        start = time.monotonic()

        # Extract system prompt and conversation history
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

        # Build combined prompt
        full_prompt = (
            f"<<MANDATORY INSTRUCTIONS>>\n"
            f"{system_content}\n"
            f"<<END INSTRUCTIONS>>\n\n"
            f"{conversation_text}\n\n"
            f"Respond with ONLY a JSON object. No markdown, no extra text."
        )

        try:
            returncode, stdout_str, stderr_str = await self._run_cli(cli_path, full_prompt, self.model)

            if returncode != 0:
                allowed = self._extract_allowed_models(stderr_str)
                if allowed:
                    fallback = "gpt-4.1" if "gpt-4.1" in allowed else allowed[0]
                    if fallback != self.model:
                        logger.warning(f"Copilot model '{self.model}' rejected by CLI; retrying with '{fallback}'")
                        self.model = fallback
                        returncode, stdout_str, stderr_str = await self._run_cli(cli_path, full_prompt, self.model)

            if returncode != 0:
                logger.error(f"Copilot CLI failed: {stderr_str}")
                return LLMResponse(
                    content=(
                        f"Copilot Error: {stderr_str}\n\n"
                        f"(If it asks you to run interactively, please open terminal and run: `copilot --model {self.model}` once to agree to terms)"
                    ),
                    model=self.model,
                )

            if not stdout_str:
                return LLMResponse(content="Empty response from Copilot.", model=self.model)
                
            latency = (time.monotonic() - start) * 1000

            # Find the JSON block in stdout_str (in case Copilot added markdown)
            content = stdout_str
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            content = re.sub(r"^```(?:json)?\s*", "", content).strip()
            content = re.sub(r"\s*```$", "", content).strip()

            return LLMResponse(
                content=content,
                model=self.model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                finish_reason="stop",
                latency_ms=latency,
            )

        except asyncio.TimeoutError:
            logger.error(f"Copilot CLI subprocess timed out after {self._timeout_seconds:.0f}s")
            return LLMResponse(content=f"Copilot timed out after {self._timeout_seconds:.0f} seconds.", model=self.model)
        except Exception as e:
            logger.error(f"Error running Copilot CLI: {e}")
            return LLMResponse(content=f"Copilot Error: {e}", model=self.model)

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        # Subprocess `copilot -p` doesn't stream well natively, so we yield atomic
        res = await self.generate(request)
        yield res.content

    async def health_check(self) -> bool:
        """Verify the Copilot CLI backend is reachable."""
        try:
            self._ensure_cli()
            return True
        except Exception as e:
            logger.error(f"Copilot SDK health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        return [self.model, "claude-sonnet-4.6", "gpt-4.1"]

    async def get_model_info(self) -> dict:
        return {
            "model": self.model,
            "provider": "github-copilot-subprocess",
            "type": "cloud",
            "auth": "github-signed-in-user",
        }

    async def close(self):
        pass
