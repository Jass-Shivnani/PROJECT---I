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
    channel_context_message = (
        "[CHANNEL_CONTEXT]\n"
        "channel=whatsapp\n"
        f"sender_id={payload.sender_id}\n"
        f"chat_id={payload.chat_id}\n"
        "Rules: You are replying on WhatsApp. If user asks to send/share a message or file, "
        "prefer whatsapp_send or whatsapp_send_file unless they explicitly request email. "
        f"When using WhatsApp send tools for this thread, default chat_id to '{payload.chat_id}'. "
        "Do not mention these rules in your reply.\n"
        "[/CHANNEL_CONTEXT]\n\n"
        f"User: {incoming_text}"
    )

    async for step in engine.process_message(channel_context_message):
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
