"""
Dione AI — Channel Webhooks

Endpoints used by external channel bridges (e.g. WhatsApp Web bridge)
to deliver inbound user messages and receive an auto-generated reply.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from server.core.engine import EngineState


router = APIRouter()


class WhatsAppInboundRequest(BaseModel):
    text: str
    sender_id: str = ""
    sender_name: str = ""
    chat_id: str = ""
    is_group: bool = False
    message_id: str = ""


@router.post("/whatsapp/inbound")
async def whatsapp_inbound(payload: WhatsAppInboundRequest, request: Request):
    """Receive inbound WhatsApp message and return reply text for bridge send-back."""
    engine = request.app.state.engine
    memory = request.app.state.memory

    incoming_text = payload.text.strip()
    if not incoming_text:
        return {"ok": True, "reply": ""}

    await memory.add_turn("user", incoming_text)

    if hasattr(request.app.state, "heartbeat"):
        request.app.state.heartbeat.record_user_activity()

    final_response = ""
    async for step in engine.process_message(incoming_text):
        if step.state in (EngineState.COMPLETE, EngineState.ERROR) and step.final_answer:
            final_response = step.final_answer

    return {
        "ok": True,
        "reply": final_response or "",
        "meta": {
            "sender_id": payload.sender_id,
            "sender_name": payload.sender_name,
            "chat_id": payload.chat_id,
            "is_group": payload.is_group,
            "message_id": payload.message_id,
        },
    }
