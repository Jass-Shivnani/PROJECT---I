"""
Dione AI — Gemini LLM Backend

Connects to Google's Gemini API for inference.
Supports native Tool/Function Calling via google-genai SDK,
multimodal vision analysis, token streaming, and resilient fallback candidates.
"""

import time
import asyncio
import uuid
from typing import AsyncGenerator, Optional, List, Dict, Any, Union
from loguru import logger

from server.llm.adapter import BaseLLMAdapter, LLMRequest, LLMResponse, LLMMessage


class GeminiAdapter(BaseLLMAdapter):
    """
    LLM adapter for Google Gemini API with native Function Calling.
    Supports Gemini 3.5 Flash-Lite, Gemini 3 Flash Preview, and Fallback models.
    """

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite"):
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

    def _convert_tools(self, tools: Optional[List[Dict[str, Any]]]):
        """Convert standard JSON schemas into google-genai types.Tool."""
        if not tools:
            return None
        from google.genai import types

        function_declarations = []
        for t in tools:
            name = t.get("name", "")
            description = t.get("description", "")
            parameters = t.get("parameters", {})
            if not name:
                continue

            # Ensure valid parameters structure
            if not isinstance(parameters, dict) or not parameters:
                parameters = {
                    "type": "OBJECT",
                    "properties": {},
                }

            try:
                fd = types.FunctionDeclaration(
                    name=name,
                    description=description,
                    parameters=parameters,
                )
                function_declarations.append(fd)
            except Exception as e:
                logger.warning(f"Failed to create FunctionDeclaration for {name}: {e}")

        if not function_declarations:
            return None

        return [types.Tool(function_declarations=function_declarations)]

    async def generate(self, request: Union[LLMRequest, str]) -> LLMResponse:
        """Generate a complete response using Gemini with native function calling."""
        if isinstance(request, str):
            request = LLMRequest(messages=[LLMMessage(role="user", content=request)])
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

        genai_tools = self._convert_tools(request.tools)

        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            tools=genai_tools,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        if request.json_mode and not genai_tools:
            config.response_mime_type = "application/json"

        # Model candidates with automatic fallback
        candidates = [self.model, "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash"]
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

                    # Parse native function calls if emitted by the model
                    tool_calls = []
                    if hasattr(response, "function_calls") and response.function_calls:
                        for fc in response.function_calls:
                            fc_name = getattr(fc, "name", "")
                            fc_args = getattr(fc, "args", {})
                            if isinstance(fc_args, dict):
                                clean_args = dict(fc_args)
                            elif hasattr(fc_args, "model_dump"):
                                clean_args = fc_args.model_dump()
                            else:
                                clean_args = dict(fc_args) if fc_args else {}

                            tool_calls.append({
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "name": fc_name,
                                "args": clean_args,
                            })

                    return LLMResponse(
                        content=content,
                        model=candidate,
                        prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
                        completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
                        total_tokens=getattr(usage, "total_token_count", 0) if usage else 0,
                        finish_reason="stop",
                        latency_ms=latency,
                        tool_calls=tool_calls,
                    )
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    is_transient = any(code in err_str for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "DeadlineExceeded"])
                    if is_transient and attempt < 2:
                        logger.warning(f"Gemini {candidate} transient ({err_str[:60]}), quick retry in 0.5s...")
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        logger.warning(f"Gemini {candidate} failed: {err_str[:100]}. Switching to next candidate model...")
                        break

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

        candidates = [self.model, "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash"]
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
        """Convert LLMMessages to Gemini content format with native function calling support."""
        from google.genai import types
        contents = []
        for msg in messages:
            if msg.role == "system":
                continue  # Handled via system_instruction

            if msg.role in ("tool", "function"):
                tool_name = msg.name or "tool_result"
                res_payload = {"result": msg.content} if isinstance(msg.content, str) else (msg.content or {})
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(name=tool_name, response=res_payload)]
                ))
            elif getattr(msg, "tool_calls", None):
                parts = []
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))
                for tc in msg.tool_calls:
                    parts.append(types.Part.from_function_call(name=tc["name"], args=tc.get("args", {})))
                contents.append(types.Content(role="model", parts=parts))
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.content or " ")]
                ))
        return contents

    async def health_check(self) -> bool:
        """Check if Gemini API is reachable across candidate models."""
        try:
            self._ensure_client()
            from google.genai import types
            candidates = [self.model, "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.1-flash-lite"]
            for cand in list(dict.fromkeys(candidates)):
                try:
                    response = self._client.models.generate_content(
                        model=cand,
                        contents="Say hi",
                        config=types.GenerateContentConfig(max_output_tokens=5),
                    )
                    if response.text is not None:
                        return True
                except Exception:
                    continue
            return False
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
            "native_function_calling": True,
        }

    async def generate_vision(self, prompt: str, image_bytes: bytes | list[bytes], json_mode: bool = False) -> str:
        """Generate response given one or multiple images and prompt using multimodal Gemini."""
        self._ensure_client()
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1024,
        )
        if json_mode:
            config.response_mime_type = "application/json"

        if isinstance(image_bytes, list):
            image_parts = [
                types.Part.from_bytes(data=img, mime_type="image/png")
                for img in image_bytes
            ]
            contents = [prompt, *image_parts]
        else:
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png",
            )
            contents = [prompt, image_part]

        candidates = [self.model, "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash"]
        candidates = list(dict.fromkeys(candidates))

        last_error = None
        for candidate in candidates:
            try:
                response = self._client.models.generate_content(
                    model=candidate,
                    contents=contents,
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
