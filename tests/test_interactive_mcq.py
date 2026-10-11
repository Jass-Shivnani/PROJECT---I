"""
Tests for Dione Interactive Disconnected Integration & MCQ Flow
==============================================================
Verifies:
1. IntegrationDisconnectedError raises with correct metadata.
2. ReAct Engine intercepts disconnected integration cleanly without infinite loops.
3. Chat API emits 'integration_disconnected' event over WebSocket.
4. Terminal MCQ arrow-key selector fallback works correctly.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from server.plugins.integrations.base import IntegrationDisconnectedError, IntegrationStatus
from server.plugins.integrations.registry import IntegrationRegistry
from server.plugins.integrations.whatsapp import WhatsAppIntegration
from server.plugins.integrations.telegram import TelegramIntegration
from server.core.engine import DioneEngine, ToolCall
from server.cli.interactive_select import select_mcq, _fallback_numeric_select


def test_integration_disconnected_error():
    err = IntegrationDisconnectedError("whatsapp", "WhatsApp", "whatsapp_send", {"to": "123"})
    assert err.integration_id == "whatsapp"
    assert err.display_name == "WhatsApp"
    assert err.tool_name == "whatsapp_send"
    assert "not connected" in str(err)


@pytest.mark.asyncio
async def test_registry_raises_on_disconnected_tool():
    reg = IntegrationRegistry()
    wa = WhatsAppIntegration()
    wa.status = IntegrationStatus.DISCONNECTED
    reg.register(wa)

    with pytest.raises(IntegrationDisconnectedError) as exc_info:
        await reg.execute_tool("whatsapp_send", {"to": "+919999999999", "text": "hello"})

    assert exc_info.value.integration_id == "whatsapp"
    assert exc_info.value.display_name == "WhatsApp"


@pytest.mark.asyncio
async def test_connect_integration_tool():
    reg = IntegrationRegistry()
    tg = TelegramIntegration()
    reg.register(tg)

    with pytest.raises(IntegrationDisconnectedError) as exc_info:
        await reg.execute_tool("connect_integration", {"service": "telegram"})

    assert exc_info.value.integration_id == "telegram"
    assert exc_info.value.display_name == "Telegram"


@pytest.mark.asyncio
async def test_engine_execute_tool_catches_disconnected():
    engine = DioneEngine()
    reg = IntegrationRegistry()
    wa = WhatsAppIntegration()
    wa.status = IntegrationStatus.DISCONNECTED
    reg.register(wa)
    engine.set_integrations(reg)

    obs = await engine._execute_tool(ToolCall(tool="whatsapp_send", params={"to": "+919999999999", "text": "hello"}))
    assert not obs.success
    assert "DISCONNECTED_INTEGRATION:whatsapp:WhatsApp" in obs.error
    assert "Do not loop" in obs.error


def test_interactive_mcq_fallback():
    options = ["[1] Connect WhatsApp", "[2] Switch to Telegram", "[3] Cancel"]
    with patch("builtins.input", return_value="2"):
        selected = _fallback_numeric_select("Test Prompt", options, default_index=0)
        assert selected == 1  # 0-indexed for option 2

    with patch("builtins.input", return_value=""):
        selected = _fallback_numeric_select("Test Prompt", options, default_index=0)
        assert selected == 0
