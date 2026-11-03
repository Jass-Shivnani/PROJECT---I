"""
Dione AI — Dual-Engine Autonomous Email Plugin
==============================================
Provides resilient email dispatch and inbox operations:
1. Engine A (Background OAuth2 / SMTP via GoogleMailIntegration & CredentialVault):
   Uses Unified Google OAuth2 or Gmail App Password stored in CredentialVault (`data/credentials/`).
2. Engine B (Human-Like Visual Browser / Webmail):
   If background credentials are not present, launches the user's active browser to Gmail Compose
   (https://mail.google.com), pre-populating recipient, subject, and body, and attempts UIA Send.
"""

import os
import re
import json
import asyncio
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

from server.plugins.base import BasePlugin, dione_tool
from server.knowledge.social_intelligence import SocialIntelligenceEngine
from server.plugins.integrations.base import CredentialVault
from server.plugins.integrations.google_mail import GoogleMailIntegration


def normalize_email_body(text: str) -> str:
    """Normalize email body: unescape literal \\n, \\r\\n, handle /n shorthand, and produce clean multiline text."""
    if not text:
        return ""
    text = str(text)
    # Unescape literal escaped newlines that came through serialized strings or LLM output
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    # Handle /n shorthand if used by user/model as a newline delimiter
    text = re.sub(r"(?<![a-zA-Z0-9])/n(?![a-zA-Z0-9])", "\n", text)
    # Normalize CRLF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


class EmailPlugin(BasePlugin):
    """Autonomous Dual-Engine email dispatch and communications."""

    name = "EmailPlugin"
    description = "Send and read emails with automatic contact name resolution and dual-engine fallback (Unified Google OAuth2, background SMTP, or visual browser compose)."
    version = "2.0.0"

    def __init__(self):
        super().__init__()
        self._social_engine = SocialIntelligenceEngine()
        self._vault = CredentialVault(data_dir="data")

    def _resolve_recipient(self, recipient: str) -> str:
        """Resolve contact name or nickname to email address."""
        raw = (recipient or "").strip()
        if "@" in raw:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw)
            return email_match.group(0) if email_match else raw

        if raw.lower() in ("myself", "me", "jass", "owner"):
            return os.getenv("DIONE_USER_EMAIL", "jass.shivnani@ves.ac.in")

        dossier = self._social_engine.resolve_person(raw)
        if dossier and dossier.email:
            logger.info(f"[EmailPlugin] Resolved contact '{raw}' -> {dossier.email} ({dossier.canonical_name})")
            return dossier.email

        for d in self._social_engine.dossiers.values():
            if raw.lower() in d.canonical_name.lower() or any(raw.lower() in a.lower() for a in d.aliases):
                logger.info(f"[EmailPlugin] Partial match for '{raw}' -> {d.email}")
                return d.email

        return raw

    def _get_gmail_integration(self) -> Optional[GoogleMailIntegration]:
        creds = self._vault.retrieve("google_mail")
        if creds and (creds.access_token or creds.api_key):
            gm = GoogleMailIntegration()
            gm.credentials = creds
            return gm
        return None

    @dione_tool(
        description=(
            "Send an email to any recipient. Supports resolving contact names directly (e.g. 'Riya' or 'Prof. Geocey' or 'riyakhialani@gmail.com'). "
            "Dual-Engine: Uses Unified Google OAuth2 / background SMTP if configured, or automatically opens browser/webmail to compose."
        ),
        permission_level="execute",
        requires_confirmation=False,
    )
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
    ) -> str:
        """Send an email using the Dual-Engine pipeline."""
        target_email = self._resolve_recipient(to)
        clean_body = normalize_email_body(body)
        logger.info(f"[EmailPlugin] Initiating send_email to '{target_email}' | Subject: '{subject}'")

        # 1. Attempt Engine A: Unified OAuth2 or Background SMTP via GoogleMailIntegration
        gm = self._get_gmail_integration()
        smtp_error = None
        if gm is not None:
            res = await gm.send_email(to=target_email, subject=subject, body=clean_body, attachments=attachments)
            if res.get("success"):
                mode = "Unified Google OAuth2 (Gmail API)" if gm._is_oauth() else "Background SMTP"
                return (
                    f"Successfully sent email to {target_email} via {mode}.\n"
                    f"- Recipient: {target_email}\n"
                    f"- Subject: {subject}\n"
                    f"- Attachments: {res.get('attachments', [])}\n"
                    f"- Delivery Mode: {mode}"
                )
            smtp_error = res.get("error")
            logger.warning(f"[EmailPlugin] Background Gmail dispatch failed ({smtp_error}); falling back to Visual Browser Engine...")

        # 2. Engine B: Visual Browser / Webmail Compose
        try:
            encoded_subject = urllib.parse.quote(subject)
            encoded_body = urllib.parse.quote(clean_body)
            encoded_to = urllib.parse.quote(target_email)

            gmail_compose_url = (
                f"https://mail.google.com/mail/?view=cm&fs=1&to={encoded_to}&su={encoded_subject}&body={encoded_body}"
            )

            from server.plugins.builtin.computer_use_plugin import ComputerUsePlugin
            cup = ComputerUsePlugin()
            await cup.open_browser(url=gmail_compose_url)

            await asyncio.sleep(2.5)
            from server.core.runtime.computer_use import get_computer_use_operator
            op = get_computer_use_operator()
            win = op.get_foreground_window_info()

            return (
                f"Email composed and staged in browser for {target_email}.\n"
                f"- Recipient: {target_email}\n"
                f"- Subject: {subject}\n"
                f"- Delivery Engine: Gmail Web Direct Compose (Active Window: \"{win.get('title')}\")\n"
                f"- Status: Compose view active with recipient, subject, and body pre-filled (press Ctrl+Enter in browser to send, or connect Google OAuth2 in Settings for silent background sending)."
            )
        except Exception as be:
            logger.error(f"[EmailPlugin] Visual browser email fallback failed: {be}")
            return f"Failed to send email to {target_email}: {smtp_error or be}"

    @dione_tool(
        description="Search or read recent emails from the Gmail inbox.",
        permission_level="read",
        requires_confirmation=False,
    )
    async def read_emails(self, count: int = 5, unread_only: bool = False) -> str:
        """Read recent emails via Unified OAuth2 or IMAP."""
        gm = self._get_gmail_integration()
        if gm is None:
            return (
                "No Gmail credentials configured for background reading yet. "
                "Connect Google OAuth2 or Gmail App Password in Settings -> Integrations & Channels."
            )

        messages = await gm.read_emails(count=count, unread_only=unread_only)
        if not messages:
            return "No matching emails found in inbox."
        if len(messages) == 1 and "error" in messages[0]:
            return f"Could not read emails: {messages[0]['error']}"

        lines = ["Recent Inbox Emails:"]
        for m in messages:
            lines.append(
                f"- [{m.get('date', '')}] From: {m.get('from', 'Unknown')} | Subject: {m.get('subject', '(No Subject)')}\n"
                f"  Preview: {m.get('body_preview', '')[:200]}"
            )
        return "\n".join(lines)
