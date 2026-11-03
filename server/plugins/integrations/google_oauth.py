"""
Dione AI — Unified Google OAuth2 Manager (v4.0 Demo-Hardened Edition)
=====================================================================
Provides single-sign-on OAuth2 across Gmail, Google Calendar, Google Drive,
and Google Photos with:
- Automatic discovery of `client_secret*.json` / `credentials.json` across `data/`,
  `data/credentials/`, project root, and `~/Downloads`.
- Automatic persistence and restoration of OAuth tokens from `data/google_oauth_token.json`
  as well as `CredentialVault` (`data/integrations/credentials.enc`).
- Graceful scope fallback if a Google Cloud Console project does not have the legacy
  Photos Library scope enabled, ensuring Unified Google OAuth2 never fails during a live demo.
"""

from __future__ import annotations

import glob
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

CORE_WORKSPACE_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

GOOGLE_SERVICE_IDS: List[str] = [
    "google_mail",
    "google_calendar",
    "google_drive",
    "google_photos",
]

TOKEN_FILE_PATHS: List[str] = [
    "data/google_oauth_token.json",
    "data/credentials/google_oauth_token.json",
    "data/credentials/token.json",
    "token.json",
]


def discover_client_secret_file(explicit_path: str = "") -> Optional[Path]:
    """Locate a Google OAuth2 client_secret.json / credentials.json file automatically."""
    candidates = [
        explicit_path,
        os.getenv("DIONE_GOOGLE_CLIENT_SECRETS", ""),
        os.getenv("DIONE_GMAIL_CREDENTIALS_PATH", ""),
        os.getenv("DIONE_GOOGLE_CALENDAR_CREDENTIALS", ""),
        "data/credentials/client_secret.json",
        "data/credentials/google_client_secret.json",
        "data/credentials/credentials.json",
        "data/client_secret.json",
        "data/credentials.json",
        "credentials.json",
        "client_secret.json",
    ]
    for cp in candidates:
        if cp and Path(cp).expanduser().is_file():
            return Path(cp).expanduser().resolve()

    # Check wildcard client_secret_*.json in project root, data/, data/credentials/, and ~/Downloads
    search_dirs = [Path.cwd(), Path("data"), Path("data/credentials"), Path.home() / "Downloads"]
    for sdir in search_dirs:
        if sdir.is_dir():
            for match in sorted(sdir.glob("client_secret*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                if match.is_file():
                    return match.resolve()
    return None


def load_saved_google_token_file() -> Optional[IntegrationCredentials]:
    """Load persisted Google OAuth2 token from disk if present."""
    for tp in TOKEN_FILE_PATHS:
        p = Path(tp)
        if p.is_file():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                token = raw.get("token") or raw.get("access_token") or ""
                refresh_token = raw.get("refresh_token") or ""
                if not token and not refresh_token:
                    continue
                expiry = None
                if raw.get("expiry"):
                    try:
                        expiry = datetime.fromisoformat(str(raw["expiry"]).replace("Z", ""))
                    except Exception:
                        expiry = None
                return IntegrationCredentials(
                    integration_id="google_unified",
                    auth_type=AuthType.OAUTH2,
                    access_token=token,
                    refresh_token=refresh_token,
                    token_expiry=expiry,
                    extra={
                        "client_id": raw.get("client_id", ""),
                        "client_secret": raw.get("client_secret", ""),
                        "token_uri": raw.get("token_uri", "https://oauth2.googleapis.com/token"),
                        "scopes": raw.get("scopes", UNIFIED_GOOGLE_SCOPES),
                        "unified_oauth": True,
                    },
                )
            except Exception as e:
                logger.debug(f"[GoogleOAuth] Could not parse token file {p}: {e}")
    return None


def save_google_token_file(creds_data: IntegrationCredentials) -> None:
    """Persist Google OAuth2 token to data/google_oauth_token.json for cross-restart resilience."""
    try:
        out_path = Path("data/google_oauth_token.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        extra = creds_data.extra or {}
        payload = {
            "token": creds_data.access_token,
            "refresh_token": creds_data.refresh_token,
            "token_uri": extra.get("token_uri", "https://oauth2.googleapis.com/token"),
            "client_id": extra.get("client_id", ""),
            "client_secret": extra.get("client_secret", ""),
            "scopes": extra.get("scopes", UNIFIED_GOOGLE_SCOPES),
            "expiry": creds_data.token_expiry.isoformat() if creds_data.token_expiry else None,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug(f"[GoogleOAuth] Could not write token file: {e}")


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
    target_scopes = scopes or extra.get("scopes") or None

    client_id = extra.get("client_id") or os.getenv("DIONE_GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID") or ""
    client_secret = extra.get("client_secret") or os.getenv("DIONE_GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET") or ""
    token_uri = extra.get("token_uri", "https://oauth2.googleapis.com/token")

    secret_file = discover_client_secret_file(str(extra.get("client_secret_path") or ""))
    if (not client_id or not client_secret) and secret_file and secret_file.exists():
        try:
            raw = json.loads(secret_file.read_text(encoding="utf-8"))
            block = raw.get("installed") or raw.get("web") or {}
            client_id = client_id or block.get("client_id", "")
            client_secret = client_secret or block.get("client_secret", "")
            token_uri = block.get("token_uri", token_uri)
        except Exception as e:
            logger.debug(f"Could not read client_secrets file {secret_file}: {e}")

    # Pass scopes=None to Credentials so Google's refresh call does not fail with invalid_scope
    # if the user granted a subset of scopes during consent.
    creds = Credentials(
        token=creds_data.access_token or None,
        refresh_token=creds_data.refresh_token or None,
        token_uri=token_uri,
        client_id=client_id or None,
        client_secret=client_secret or None,
    )

    if creds_data.token_expiry:
        creds.expiry = creds_data.token_expiry.replace(tzinfo=None)

    if (not creds.token or creds.expired) and creds.refresh_token and client_id and client_secret:
        try:
            creds.refresh(Request())
            creds_data.access_token = creds.token or creds_data.access_token
            creds_data.token_expiry = creds.expiry
            save_google_token_file(creds_data)
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
    2. Persisted token file (`data/google_oauth_token.json` / `token.json`) if valid
    3. Local OAuth2 InstalledAppFlow using discovered `client_secret*.json` or inline `client_id` + `client_secret`
       (with automatic fallback to CORE_WORKSPACE_SCOPES if Photos scope is not enabled in GCP)
    """
    import asyncio

    target_scopes = scopes or UNIFIED_GOOGLE_SCOPES
    access_token = str(params.get("access_token") or os.getenv("DIONE_GOOGLE_ACCESS_TOKEN") or "").strip()
    refresh_token = str(params.get("refresh_token") or os.getenv("DIONE_GOOGLE_REFRESH_TOKEN") or "").strip()
    client_id = str(params.get("client_id") or os.getenv("DIONE_GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID") or "").strip()
    client_secret = str(params.get("client_secret") or os.getenv("DIONE_GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()

    if access_token:
        ic = IntegrationCredentials(
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
        save_google_token_file(ic)
        return ic

    # Check if a saved token file already exists on disk and can be refreshed/used
    if not params.get("force_reauth"):
        saved_ic = load_saved_google_token_file()
        if saved_ic and (saved_ic.access_token or saved_ic.refresh_token):
            try:
                c = build_google_credentials_object(saved_ic)
                if c and c.token:
                    saved_ic.access_token = c.token
                    return saved_ic
            except Exception:
                pass

    secret_file = discover_client_secret_file(str(params.get("client_secret_path") or ""))

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

    # Allow relaxed scope matching so Google doesn't raise Warning/Exception when scopes differ
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        loop = asyncio.get_running_loop()

        def _execute_flow(flow_scopes: List[str]):
            if secret_file:
                flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), flow_scopes)
            else:
                flow = InstalledAppFlow.from_client_config(client_config, flow_scopes)
            return flow.run_local_server(port=0, prompt="consent")

        try:
            creds = await loop.run_in_executor(None, _execute_flow, target_scopes)
        except Exception as first_err:
            logger.warning(f"[GoogleOAuth] Full scope OAuth flow note ({first_err}); retrying with core Workspace scopes...")
            creds = await loop.run_in_executor(None, _execute_flow, CORE_WORKSPACE_SCOPES)

        ic = IntegrationCredentials(
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
                "scopes": list(creds.scopes or target_scopes),
                "unified_oauth": True,
            },
        )
        save_google_token_file(ic)
        return ic
    except Exception as e:
        logger.error(f"[GoogleOAuth] Unified OAuth2 flow failed: {e}")
        return None
