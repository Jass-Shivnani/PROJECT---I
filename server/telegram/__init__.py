"""
Dione AI — Telegram Bot & Polling Service
=========================================
Cloud-native, zero-dependency Telegram Bot manager.
Connects directly to Telegram Bot API using async httpx.
Allows talking to Dione remotely from Telegram on your phone.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from loguru import logger
import httpx

from server.core.engine import DioneEngine, EngineState


class TelegramBotService:
    """
    Background worker that polls Telegram for incoming messages
    and routes them through Dione's core engine.
    """

    API_BASE = "https://api.telegram.org"

    def __init__(
        self,
        bot_token: str,
        engine: DioneEngine,
        allowed_chat_id: Optional[str] = None,
        poll_interval: float = 1.0,
    ):
        self.bot_token = bot_token
        self.engine = engine
        self.allowed_chat_id = str(allowed_chat_id).strip() if allowed_chat_id else None
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_update_id = 0
        self.bot_info: Dict[str, Any] = {}

    async def start(self) -> bool:
        """Verify token and start background long-polling loop."""
        if not self.bot_token:
            logger.warning("TelegramBotService: No bot token configured")
            return False

        try:
            url = f"{self.API_BASE}/bot{self.bot_token}/getMe"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200 or not resp.json().get("ok"):
                    logger.error(f"Telegram bot validation failed: {resp.text}")
                    return False
                self.bot_info = resp.json().get("result", {})
                logger.info(f"✨ Telegram Bot verified: @{self.bot_info.get('username')}")

        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return False

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("🚀 Telegram background polling active")
        return True

    async def stop(self):
        """Stop background polling."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Telegram background polling stopped")

    async def _poll_loop(self):
        """Long-polling update loop."""
        url = f"{self.API_BASE}/bot{self.bot_token}/getUpdates"

        while self._running:
            try:
                params = {
                    "offset": self._last_update_id + 1,
                    "timeout": 20,
                    "allowed_updates": ["message"],
                }

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params)

                    if resp.status_code == 200:
                        data = resp.json()
                        updates = data.get("result", [])

                        for update in updates:
                            self._last_update_id = update["update_id"]
                            message = update.get("message", {})
                            await self._handle_inbound_message(message)

                    elif resp.status_code == 409:
                        logger.warning("Telegram conflict: Another bot instance is polling. Waiting 10s...")
                        await asyncio.sleep(10)
                    else:
                        await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Telegram poll error: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _handle_inbound_message(self, message: Dict[str, Any]):
        """Process message from Telegram user through DioneEngine."""
        if not message:
            return

        chat_id = str(message.get("chat", {}).get("id"))
        user_name = message.get("from", {}).get("first_name", "User")
        text = message.get("text", "").strip()

        if not text:
            return

        # Security check: If allowed_chat_id is specified, ignore unauthorized chats
        if self.allowed_chat_id and chat_id != self.allowed_chat_id:
            logger.warning(f"Unauthorized Telegram message from chat_id {chat_id} ({user_name})")
            await self._send_reply(chat_id, "🔒 Dione is configured for private single-user access. This chat is not authorized.")
            return

        logger.info(f"📱 Telegram Inbound from {user_name} ({chat_id}): {text}")

        # Built-in quick commands
        if text == "/start":
            greeting = (
                f"🌙 *Hello {user_name}! I am Dione.*\n\n"
                "I am your personal AI assistant running on your workstation.\n"
                "You can chat with me, ask me to search the web, manage files, or run actions.\n\n"
                f"*Your Chat ID:* `{chat_id}`"
            )
            await self._send_reply(chat_id, greeting)
            return

        if text == "/status":
            state = self.engine.get_alive_state()
            mood = state.get("mood", {}).get("label", "balanced")
            await self._send_reply(chat_id, f"⚡ *Dione Status:* Online\n🎭 *Mood:* {mood}\n🧠 *Model:* Gemini 3.5 Flash Lite")
            return

        # Send typing action
        await self._send_chat_action(chat_id, "typing")

        # Process through Dione cognitive engine
        final_answer = ""
        try:
            res = self.engine.process_message(text)
            if hasattr(res, "__aiter__"):
                async for step in res:
                    if hasattr(step, "state") and step.state in (EngineState.COMPLETE, EngineState.ERROR) and getattr(step, "final_answer", None):
                        final_answer = step.final_answer
            elif asyncio.iscoroutine(res):
                out = await res
                if isinstance(out, dict):
                    final_answer = out.get("response", "") or out.get("reply", "") or str(out)
                else:
                    final_answer = str(out)
            elif isinstance(res, dict):
                final_answer = res.get("response", "") or str(res)
        except Exception as e:
            logger.error(f"Error processing Telegram message: {e}")
            final_answer = f"Sorry, I ran into an error while thinking: {e}"

        if not final_answer:
            final_answer = "I processed your request, but did not generate a response."

        await self._send_reply(chat_id, final_answer)

    async def _send_chat_action(self, chat_id: str, action: str = "typing"):
        try:
            url = f"{self.API_BASE}/bot{self.bot_token}/sendChatAction"
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json={"chat_id": chat_id, "action": action})
        except Exception:
            pass

    async def _send_reply(self, chat_id: str, text: str):
        """Send message back to Telegram."""
        try:
            url = f"{self.API_BASE}/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    # Retry as plain text if markdown formatting failed
                    payload.pop("parse_mode", None)
                    await client.post(url, json=payload)
        except Exception as e:
            logger.error(f"Failed to send Telegram reply: {e}")
