"""
Dione AI — Unified Google OAuth2 Manager
========================================
Provides single-sign-on OAuth2 across Gmail, Google Calendar, Google Drive,
and Google Photos with automatic token refresh and shared credential storage.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from server.plugins.types import AuthType, IntegrationCredentials

UNIFIED_GOOGLE_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
]

GOOGLE_SERVICE_IDS: List[str] = [
    "google_mail",
    "google_calendar",
    "google_drive",
    "google_photos",
]


def build_google_credentials_object(
    creds_data: IntegrationCredentials,
    scopes: Optional[List[str]] = None,
    vault: Any = None,
):
    """
    Construct a google.oauth2.credentials.Credentials instance from IntegrationCredentials
    and automatically refresh if expired.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    extra = creds_data.extra or {}
    target_scopes = scopes or extra.get("scopes") or UNIFIED_GOOGLE_SCOPES

    client_id = extra.get("client_id") or os.getenv("DIONE_GOOGLE_CLIENT_ID", "")
    client_secret = extra.get("client_secret") or os.getenv("DIONE_GOOGLE_CLIENT_SECRET", "")
    token_uri = extra.get("token_uri", "https://oauth2.googleapis.com/token")

    # If a client_secret_path exists, extract client_id/client_secret if missing
    secret_path = extra.get("client_secret_path") or os.getenv("DIONE_GOOGLE_CALENDAR_CREDENTIALS") or os.getenv("DIONE_GMAIL_CREDENTIALS_PATH")
    if (not client_id or not client_secret) and secret_path and Path(secret_path).exists():
        try:
            raw = json.loads(Path(secret_path).read_text(encoding="utf-8"))
            block = raw.get("installed") or raw.get("web") or {}
            client_id = client_id or block.get("client_id", "")
            client_secret = client_secret or block.get("client_secret", "")
            token_uri = block.get("token_uri", token_uri)
        except Exception as e:
            logger.debug(f"Could not read client_secrets file {secret_path}: {e}")

    creds = Credentials(
        token=creds_data.access_token,
        refresh_token=creds_data.refresh_token or None,
        token_uri=token_uri,
        client_id=client_id or None,
        client_secret=client_secret or None,
        scopes=target_scopes,
    )

    if creds_data.token_expiry:
        creds.expiry = creds_data.token_expiry.replace(tzinfo=None)

    if creds.expired and creds.refresh_token and client_id and client_secret:
        try:
            creds.refresh(Request())
            creds_data.access_token = creds.token or creds_data.access_token
            creds_data.token_expiry = creds.expiry
            if vault is not None:
                vault.store(creds_data.integration_id, creds_data)
                vault.store("google_unified", creds_data)
            logger.info(f"[GoogleOAuth] Refreshed OAuth2 access token for {creds_data.integration_id}")
        except Exception as refresh_err:
            logger.warning(f"[GoogleOAuth] Token refresh warning: {refresh_err}")

    return creds


async def run_unified_google_oauth(params: Dict[str, Any], scopes: Optional[List[str]] = None) -> Optional[IntegrationCredentials]:
    """
    Authenticate with Google via:
    1. Direct access_token (+ optional refresh_token, client_id, client_secret)
    2. Local OAuth2 InstalledAppFlow using client_secret_path or inline client_config
    3. Environment variable fallback (DIONE_GOOGLE_CLIENT_SECRETS / data/credentials/client_secret.json)
    """
    import asyncio

    target_scopes = scopes or UNIFIED_GOOGLE_SCOPES
    access_token = str(params.get("access_token", "")).strip()
    refresh_token = str(params.get("refresh_token", "")).strip()
    client_id = str(params.get("client_id") or os.getenv("DIONE_GOOGLE_CLIENT_ID", "")).strip()
    client_secret = str(params.get("client_secret") or os.getenv("DIONE_GOOGLE_CLIENT_SECRET", "")).strip()

    if access_token:
        return IntegrationCredentials(
            integration_id="google_unified",
            auth_type=AuthType.OAUTH2,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=datetime.now() + timedelta(hours=1),
            extra={
                "client_id": client_id,
                "client_secret": client_secret,
                "token_uri": params.get("token_uri", "https://oauth2.googleapis.com/token"),
                "scopes": target_scopes,
                "email": params.get("email", ""),
                "unified_oauth": True,
            },
        )

    # Check for client_secret_path or default paths
    candidate_paths = [
        params.get("client_secret_path", ""),
        os.getenv("DIONE_GMAIL_CREDENTIALS_PATH", ""),
        os.getenv("DIONE_GOOGLE_CALENDAR_CREDENTIALS", ""),
        "data/credentials/client_secret.json",
        "data/credentials/google_client_secret.json",
        "client_secret.json",
    ]
    secret_file: Optional[Path] = None
    for cp in candidate_paths:
        if cp and Path(cp).expanduser().exists():
            secret_file = Path(cp).expanduser().resolve()
            break

    client_config = params.get("client_config")
    if not client_config and client_id and client_secret:
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

    if not secret_file and not client_config:
        logger.warning(
            "[GoogleOAuth] No access_token, client_secret.json, or client_id/client_secret provided for Google OAuth2."
        )
        return None

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        loop = asyncio.get_running_loop()

        def _execute_flow():
            if secret_file:
                flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), target_scopes)
            else:
                flow = InstalledAppFlow.from_client_config(client_config, target_scopes)
            return flow.run_local_server(port=0, prompt="consent")

        creds = await loop.run_in_executor(None, _execute_flow)
        return IntegrationCredentials(
            integration_id="google_unified",
            auth_type=AuthType.OAUTH2,
            access_token=creds.token or "",
            refresh_token=creds.refresh_token or "",
            token_expiry=creds.expiry,
            extra={
                "client_secret_path": str(secret_file) if secret_file else "",
                "client_id": creds.client_id or client_id,
                "client_secret": getattr(creds, "client_secret", "") or client_secret,
                "token_uri": creds.token_uri or "https://oauth2.googleapis.com/token",
                "scopes": target_scopes,
                "unified_oauth": True,
            },
        )
    except Exception as e:
        logger.error(f"[GoogleOAuth] Unified OAuth2 flow failed: {e}")
        return None
