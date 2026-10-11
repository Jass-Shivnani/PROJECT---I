"""
Google Mail (Gmail) Integration Plugin
"""

from __future__ import annotations

import json
import asyncio
import mimetypes
from datetime import datetime
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


class GoogleMailIntegration(BaseIntegration):
    """
    Gmail — read, search, compose, and send emails.
    
    Uses IMAP for reading and SMTP for sending via Python stdlib.
    Requires an App Password (not regular password) for Gmail.
    """
    
    INTEGRATION_ID = "google_mail"
    DISPLAY_NAME = "Gmail"
    DESCRIPTION = "Read, search, and send emails via Gmail"
    AUTH_TYPE = AuthType.API_KEY  # App password
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = []

    IMAP_HOST = "imap.gmail.com"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        email = params.get("email", "")
        app_password = params.get("app_password", params.get("api_key", ""))
        if not email and self.credentials:
            email = self.credentials.extra.get("email", "")
        if not app_password and self.credentials:
            app_password = self.credentials.api_key
        if not email or not app_password:
            return False
        
        self.credentials = IntegrationCredentials(
            integration_id=self.INTEGRATION_ID,
            auth_type=AuthType.API_KEY,
            api_key=app_password,
            extra={"email": email},
        )
        return True
    
    async def test_connection(self) -> bool:
        if not self.credentials:
            return False
        try:
            import imaplib
            email = self.credentials.extra.get("email", "")
            password = self.credentials.api_key
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
            mail.login(email, password)
            mail.logout()
            return True
        except Exception as e:
            logger.error(f"Gmail IMAP test failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        """Fetch unread count and recent subjects."""
        if not self.credentials:
            return {"error": "Not authenticated"}
        try:
            import imaplib
            email = self.credentials.extra.get("email", "")
            password = self.credentials.api_key
            
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
            mail.login(email, password)
            mail.select("INBOX")
            
            _, data = mail.search(None, "UNSEEN")
            unread_ids = data[0].split() if data[0] else []
            
            _, all_data = mail.search(None, "ALL")
            total = len(all_data[0].split()) if all_data[0] else 0
            
            mail.logout()
            
            self.last_sync = datetime.now()
            return {
                "unread": len(unread_ids),
                "total_messages": total,
                "synced_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Gmail sync error: {e}")
            return {"error": str(e)}
    
    async def read_emails(self, folder: str = "INBOX", count: int = 5,
                          unread_only: bool = False) -> list[dict]:
        """Read recent emails from a folder."""
        if not self.credentials:
            return []
        try:
            import imaplib
            import email as email_lib
            from email.header import decode_header
            
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
            mail.login(
                self.credentials.extra.get("email", ""),
                self.credentials.api_key,
            )
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
        except Exception as e:
            logger.error(f"Gmail read error: {e}")
            return [{"error": str(e)}]
    
    async def send_email(self, to: str, subject: str, body: str, attachments: list[str] | None = None) -> dict:
        """Send an email via SMTP."""
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase        
            from email import encoders
            
            sender = self.credentials.extra.get("email", "")
            password = self.credentials.api_key
            attachment_paths = attachments or []
            
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            attached_files: list[str] = []
            for raw_path in attachment_paths:
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
            
            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to}: {subject}")
            return {"success": True, "to": to, "subject": subject, "attachments": attached_files}
        except Exception as e:
            logger.error(f"Gmail send error: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_emails(self, query: str, folder: str = "INBOX",
                            count: int = 10) -> list[dict]:
        """Search emails by subject/sender using IMAP search."""
        if not self.credentials:
            return []
        try:
            import imaplib
            import email as email_lib
            from email.header import decode_header
            
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
            mail.login(
                self.credentials.extra.get("email", ""),
                self.credentials.api_key,
            )
            mail.select(folder)
            
            # IMAP search by subject or from
            _, data = mail.search(None, f'(OR SUBJECT "{query}" FROM "{query}")')
            ids = data[0].split() if data[0] else []
            
            results = []
            for mid in ids[-count:]:
                _, msg_data = mail.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
                header = msg_data[0][1].decode("utf-8", errors="replace")
                results.append({"id": mid.decode(), "header": header.strip()})
            
            mail.logout()
            return results
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
                    "unread_only": {"type": "boolean", "description": "Only show unread emails"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_search",
                "description": "Search Gmail by subject or sender keyword",
                "parameters": {"query": {"type": "string", "description": "Search keyword"}},
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "gmail_send",
                "description": "Compose and send an email via Gmail (supports file attachments)",
                "parameters": {
                    "to": {"type": "string", "description": "Recipient email address"},
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
                "description": "Send an email with an actual file attachment (not file contents)",
                "parameters": {
                    "to": {"type": "string", "description": "Recipient email address"},
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
