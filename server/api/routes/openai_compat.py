"""
Dione AI — OpenAI-Compatible API Gateway

Exposes standard /v1/models and /v1/chat/completions endpoints.
Allows ANY open-source frontend (LobeChat, Open WebUI, NextChat, LibreChat,
Chatbox, Cherry Studio) to connect directly to Dione's backend.
"""

import json
import time
import uuid
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

from server.core.engine import EngineState

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Any]] = ""
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "dione-core"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None


@router.get("/models")
async def list_models(request: Request):
    """List available models in OpenAI format."""
    return {
        "object": "list",
        "data": [
            {
                "id": "dione-core",
                "object": "model",
                "created": 1700000000,
                "owned_by": "dione-os",
                "permission": [],
                "root": "dione-core",
                "parent": None,
            },
            {
                "id": "dione-vision",
                "object": "model",
                "created": 1700000000,
                "owned_by": "dione-os",
                "permission": [],
                "root": "dione-vision",
                "parent": None,
            },
        ],
    }


@router.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request):
    """Standard OpenAI-compatible chat completions endpoint."""
    engine = request.app.state.engine
    if not engine:
        raise HTTPException(status_code=500, detail="Dione engine not initialized")

    if not req.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Extract the latest user prompt
    last_user_msg = ""
    for m in reversed(req.messages):
        if m.role == "user":
            if isinstance(m.content, str):
                last_user_msg = m.content
            elif isinstance(m.content, list):
                # Multimodal or part array
                parts = []
                for p in m.content:
                    if isinstance(p, dict) and p.get("type") == "text":
                        parts.append(p.get("text", ""))
                    elif isinstance(p, str):
                        parts.append(p)
                last_user_msg = " ".join(parts)
            break

    if not last_user_msg:
        last_user_msg = "Hello"

    call_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    # Streaming mode (SSE)
    if req.stream:
        async def event_generator():
            try:
                # 1. Role chunk
                first_chunk = {
                    "id": call_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": req.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(first_chunk)}\n\n"

                # 2. Process message through Dione ReAct Engine
                async for step in engine.process_message(last_user_msg):
                    if step.state == EngineState.ACTING and step.tool_call:
                        # Stream subtle tool notification
                        tool_delta = f"\n*[Dione: Executing {step.tool_call.tool}...]*\n"
                        chunk = {
                            "id": call_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": req.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": tool_delta},
                                    "finish_reason": None,
                                }
                            ],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                    elif step.state in (EngineState.COMPLETE, EngineState.ERROR) and step.final_answer:
                        chunk = {
                            "id": call_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": req.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": step.final_answer},
                                    "finish_reason": "stop",
                                }
                            ],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                # 3. Final stop marker
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"[OpenAI Compat] Stream error: {e}")
                err_chunk = {
                    "id": call_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": req.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"\n\nError: {str(e)}"},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming mode
    final_text = ""
    async for step in engine.process_message(last_user_msg):
        if step.state in (EngineState.COMPLETE, EngineState.ERROR) and step.final_answer:
            final_text = step.final_answer

    return {
        "id": call_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": final_text or "Task completed, sir.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(last_user_msg) // 4,
            "completion_tokens": len(final_text) // 4,
            "total_tokens": (len(last_user_msg) + len(final_text)) // 4,
        },
    }
