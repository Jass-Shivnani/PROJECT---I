"""
Google Mail (Gmail) Integration Plugin
Supports both Unified Google OAuth2 (Gmail REST API v1) and App Passwords (IMAP/SMTP).
"""

from __future__ import annotations

import base64
import json
import asyncio
import mimetypes
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from loguru import logger
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import email as email_lib
from email.header import decode_header

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration
from .google_oauth import build_google_credentials_object, run_unified_google_oauth, UNIFIED_GOOGLE_SCOPES


def normalize_email_body(text: str) -> str:
    """Normalize email body: unescape literal \\n, \\r\\n, handle /n shorthand, and produce clean multiline text."""
    if not text:
        return ""
    text = str(text)
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    text = re.sub(r"(?<![a-zA-Z0-9])/n(?![a-zA-Z0-9])", "\n", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


class GoogleMailIntegration(BaseIntegration):
    """
    Gmail — read, search, compose, draft, and send emails.
    Supports Unified Google OAuth2 (Gmail API v1) or App Password (IMAP/SMTP).
    """
    
    INTEGRATION_ID = "google_mail"
    DISPLAY_NAME = "Gmail"
    DESCRIPTION = "Read, search, draft, and send emails via Gmail (Unified OAuth2 or App Password)"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    IMAP_HOST = "imap.gmail.com"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587

    def _is_oauth(self) -> bool:
        return bool(
            self.credentials
            and (self.credentials.auth_type == AuthType.OAUTH2 or self.credentials.access_token)
            and not self.credentials.api_key
        )

    def _get_gmail_service(self):
        from googleapiclient.discovery import build
        creds = build_google_credentials_object(self.credentials, scopes=UNIFIED_GOOGLE_SCOPES)
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    async def authenticate(self, params: dict[str, Any]) -> bool:
        # Option 1: App Password mode
        email_addr = str(params.get("email", "")).strip()
        app_password = str(params.get("app_password") or params.get("api_key") or "").strip()
        if email_addr and app_password:
            self.credentials = IntegrationCredentials(
                integration_id=self.INTEGRATION_ID,
                auth_type=AuthType.API_KEY,
                api_key=app_password,
                extra={"email": email_addr, "mode": "app_password"},
            )
            return True

        # Option 2: Unified Google OAuth2 mode
        oauth_creds = await run_unified_google_oauth(params, scopes=UNIFIED_GOOGLE_SCOPES)
        if oauth_creds:
            oauth_creds.integration_id = self.INTEGRATION_ID
            self.credentials = oauth_creds
            return True

        # Option 3: Existing credentials already loaded
        if self.credentials and (self.credentials.access_token or self.credentials.api_key):
            return True

        return False
    
    async def test_connection(self) -> bool:
        if not self.credentials:
            return False
        loop = asyncio.get_running_loop()
        if self._is_oauth():
            try:
                def _test_oauth():
                    service = self._get_gmail_service()
                    profile = service.users().getProfile(userId="me").execute()
                    if profile.get("emailAddress"):
                        self.credentials.extra["email"] = profile["emailAddress"]
                    return True
                return await loop.run_in_executor(None, _test_oauth)
            except Exception as e:
                logger.error(f"Gmail OAuth2 test failed: {e}")
                return False
        else:
            try:
                def _test_imap():
                    email_addr = self.credentials.extra.get("email", "")
                    password = self.credentials.api_key
                    mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
                    mail.login(email_addr, password)
                    mail.logout()
                    return True
                return await loop.run_in_executor(None, _test_imap)
            except Exception as e:
                logger.error(f"Gmail IMAP test failed: {e}")
                return False
    
    async def sync(self) -> dict[str, Any]:
        """Fetch unread count and total messages."""
        if not self.credentials:
            return {"error": "Not authenticated"}
        loop = asyncio.get_running_loop()
        if self._is_oauth():
            try:
                def _sync_oauth():
                    service = self._get_gmail_service()
                    profile = service.users().getProfile(userId="me").execute()
                    unread_res = service.users().messages().list(userId="me", q="is:unread in:inbox", maxResults=50).execute()
                    unread_list = unread_res.get("messages", [])
                    return {
                        "email": profile.get("emailAddress", ""),
                        "unread": unread_res.get("resultSizeEstimate", len(unread_list)),
                        "total_messages": profile.get("messagesTotal", 0),
                        "auth_mode": "oauth2",
                        "synced_at": datetime.now().isoformat(),
                    }
                res = await loop.run_in_executor(None, _sync_oauth)
                self.last_sync = datetime.now()
                return res
            except Exception as e:
                logger.error(f"Gmail OAuth sync error: {e}")
                return {"error": str(e)}
        try:
            def _sync_imap():
                email_addr = self.credentials.extra.get("email", "")
                password = self.credentials.api_key
                mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
                mail.login(email_addr, password)
                mail.select("INBOX")
                _, data = mail.search(None, "UNSEEN")
                unread_ids = data[0].split() if data[0] else []
                _, all_data = mail.search(None, "ALL")
                total = len(all_data[0].split()) if all_data[0] else 0
                mail.logout()
                return {
                    "email": email_addr,
                    "unread": len(unread_ids),
                    "total_messages": total,
                    "auth_mode": "app_password",
                    "synced_at": datetime.now().isoformat(),
                }
            res = await loop.run_in_executor(None, _sync_imap)
            self.last_sync = datetime.now()
            return res
        except Exception as e:
            logger.error(f"Gmail sync error: {e}")
            return {"error": str(e)}
    
    async def read_emails(self, folder: str = "INBOX", count: int = 5, unread_only: bool = False) -> list[dict]:
        """Read recent emails from inbox."""
        if not self.credentials:
            return []
        loop = asyncio.get_running_loop()
        if self._is_oauth():
            try:
                def _read_oauth():
                    service = self._get_gmail_service()
                    q = "in:inbox is:unread" if unread_only else "in:inbox"
                    res = service.users().messages().list(userId="me", q=q, maxResults=max(1, min(int(count), 25))).execute()
                    messages = res.get("messages", [])
                    results = []
                    for m in messages:
                        msg_detail = service.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "To", "Subject", "Date"]).execute()
                        headers = {h["name"].lower(): h["value"] for h in msg_detail.get("payload", {}).get("headers", [])}
                        results.append({
                            "id": m["id"],
                            "from": headers.get("from", ""),
                            "to": headers.get("to", ""),
                            "subject": headers.get("subject", "(No Subject)"),
                            "date": headers.get("date", ""),
                            "body_preview": msg_detail.get("snippet", ""),
                        })
                    return results
                return await loop.run_in_executor(None, _read_oauth)
            except Exception as e:
                logger.error(f"Gmail OAuth read error: {e}")
                return [{"error": str(e)}]

        try:
            def _read_imap():
                mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
                mail.login(self.credentials.extra.get("email", ""), self.credentials.api_key)
                mail.select(folder)
                criteria = "UNSEEN" if unread_only else "ALL"
                _, data = mail.search(None, criteria)
                ids = data[0].split() if data[0] else []
                results = []
                for mid in ids[-count:]:
                    _, msg_data = mail.fetch(mid, "(RFC822)")
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)
                    subject = ""
                    raw_subject = msg.get("Subject", "")
                    if raw_subject:
                        decoded = decode_header(raw_subject)
                        subject = decoded[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(decoded[0][1] or "utf-8", errors="replace")
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                charset = part.get_content_charset() or "utf-8"
                                body = part.get_payload(decode=True).decode(charset, errors="replace")
                                break
                    else:
                        charset = msg.get_content_charset() or "utf-8"
                        body = msg.get_payload(decode=True).decode(charset, errors="replace")
                    results.append({
                        "id": mid.decode(),
                        "from": msg.get("From", ""),
                        "to": msg.get("To", ""),
                        "subject": subject,
                        "date": msg.get("Date", ""),
                        "body_preview": body[:500] if body else "",
                    })
                mail.logout()
                return results
            return await loop.run_in_executor(None, _read_imap)
        except Exception as e:
            logger.error(f"Gmail read error: {e}")
            return [{"error": str(e)}]
    
    def _build_mime_message(self, sender: str, to: str, subject: str, body: str, attachments: list[str] | None = None) -> tuple[MIMEMultipart, list[str]]:
        msg = MIMEMultipart("alternative")
        if sender:
            msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject

        clean_body = normalize_email_body(body)
        msg.attach(MIMEText(clean_body, "plain", "utf-8"))

        # HTML formatted version with line breaks and clean typography
        escaped_html = clean_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>\n")
        html_content = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b;">{escaped_html}</div>"""
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        attached_files: list[str] = []
        for raw_path in (attachments or []):
            try:
                abs_path = Path(raw_path).expanduser().resolve()
                if not abs_path.exists() or not abs_path.is_file():
                    logger.warning(f"Skipping missing attachment: {raw_path}")
                    continue
                ctype, _ = mimetypes.guess_type(str(abs_path))
                if not ctype:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)
                with open(abs_path, "rb") as fh:
                    payload = fh.read()
                part = MIMEBase(maintype, subtype)
                part.set_payload(payload)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{abs_path.name}"')
                msg.attach(part)
                attached_files.append(str(abs_path))
            except Exception as attachment_error:
                logger.warning(f"Failed to attach file '{raw_path}': {attachment_error}")
        return msg, attached_files

    async def send_email(self, to: str, subject: str, body: str, attachments: list[str] | None = None) -> dict:
        """Send an email via Gmail OAuth2 REST API or SMTP."""
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}

        # Resolve recipient name via SocialIntelligenceEngine if not an email address
        if "@" not in to:
            try:
                from server.knowledge.social_intelligence import SocialIntelligenceEngine
                dossier = SocialIntelligenceEngine().resolve_person(to)
                if dossier and dossier.email:
                    to = dossier.email
            except Exception:
                pass

        sender = self.credentials.extra.get("email", "me")
        msg, attached_files = self._build_mime_message(sender if "@" in sender else "", to, subject, body, attachments)
        loop = asyncio.get_running_loop()

        if self._is_oauth():
            try:
                def _send_oauth():
                    service = self._get_gmail_service()
                    raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
                    sent = service.users().messages().send(userId="me", body={"raw": raw_b64}).execute()
                    return sent.get("id", "")
                msg_id = await loop.run_in_executor(None, _send_oauth)
                logger.info(f"Email sent via Gmail OAuth2 API to {to}: {subject} (id={msg_id})")
                return {"success": True, "to": to, "subject": subject, "message_id": msg_id, "attachments": attached_files}
            except Exception as e:
                logger.error(f"Gmail OAuth2 send error: {e}")
                return {"success": False, "error": str(e)}

        try:
            def _send_smtp():
                password = self.credentials.api_key
                with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT, timeout=15.0) as server:
                    server.starttls()
                    server.login(sender, password)
                    server.send_message(msg)
            await loop.run_in_executor(None, _send_smtp)
            logger.info(f"Email sent via SMTP to {to}: {subject}")
            return {"success": True, "to": to, "subject": subject, "attachments": attached_files}
        except Exception as e:
            logger.error(f"Gmail SMTP send error: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_emails(self, query: str, folder: str = "INBOX", count: int = 10) -> list[dict]:
        """Search emails by keyword, sender, or subject."""
        if not self.credentials:
            return []
        loop = asyncio.get_running_loop()
        if self._is_oauth():
            try:
                def _search_oauth():
                    service = self._get_gmail_service()
                    res = service.users().messages().list(userId="me", q=query, maxResults=max(1, min(int(count), 25))).execute()
                    messages = res.get("messages", [])
                    results = []
                    for m in messages:
                        msg_detail = service.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
                        headers = {h["name"].lower(): h["value"] for h in msg_detail.get("payload", {}).get("headers", [])}
                        results.append({
                            "id": m["id"],
                            "from": headers.get("from", ""),
                            "subject": headers.get("subject", ""),
                            "date": headers.get("date", ""),
                            "snippet": msg_detail.get("snippet", ""),
                        })
                    return results
                return await loop.run_in_executor(None, _search_oauth)
            except Exception as e:
                logger.error(f"Gmail OAuth search error: {e}")
                return [{"error": str(e)}]

        try:
            def _search_imap():
                mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
                mail.login(self.credentials.extra.get("email", ""), self.credentials.api_key)
                mail.select(folder)
                _, data = mail.search(None, f'(OR SUBJECT "{query}" FROM "{query}")')
                ids = data[0].split() if data[0] else []
                results = []
                for mid in ids[-count:]:
                    _, msg_data = mail.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
                    header = msg_data[0][1].decode("utf-8", errors="replace")
                    results.append({"id": mid.decode(), "header": header.strip()})
                mail.logout()
                return results
            return await loop.run_in_executor(None, _search_imap)
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return [{"error": str(e)}]
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "gmail_read",
                "description": "Read recent emails from Gmail inbox. Returns subject, sender, date, and preview.",
                "parameters": {
                    "count": {"type": "integer", "description": "Number of emails to fetch (default 5)"},
                    "unread_only": {"type": "boolean", "description": "Only show unread emails (optional, default false)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_search",
                "description": "Search Gmail by subject, sender, or query keyword",
                "parameters": {
                    "query": {"type": "string", "description": "Search keyword or Gmail query"},
                    "count": {"type": "integer", "description": "Max results (default 10)"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_send",
                "description": "Compose and send an email via Gmail (supports contact names and file attachments)",
                "parameters": {
                    "to": {"type": "string", "description": "Recipient email address or contact name"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body text"},
                    "file_path": {"type": "string", "description": "Optional file path to attach"},
                    "file_query": {"type": "string", "description": "Optional filename/path search query to auto-find file"},
                    "search_root": {"type": "string", "description": "Optional root directory for file_query (default current workspace)"},
                    "attachments": {"type": "array", "description": "Optional list of file paths to attach"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_send_file",
                "description": "Send an email with a local file attachment",
                "parameters": {
                    "to": {"type": "string", "description": "Recipient email address or contact name"},
                    "file_path": {"type": "string", "description": "Local file path to attach"},
                    "file_query": {"type": "string", "description": "Optional filename/path search query if file_path unknown"},
                    "search_root": {"type": "string", "description": "Optional root directory for file_query"},
                    "subject": {"type": "string", "description": "Optional email subject line"},
                    "body": {"type": "string", "description": "Optional email body text"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_unread_count",
                "description": "Get the number of unread emails in inbox",
                "parameters": {},
                "integration": self.INTEGRATION_ID,
            },
        ]
