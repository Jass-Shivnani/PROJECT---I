"""
Google Calendar Integration Plugin
Full Google Calendar API v3 implementation using Unified Google OAuth2.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from loguru import logger

from server.plugins.types import AuthType, IntegrationCredentials, Permission
from .base import BaseIntegration
from .google_oauth import build_google_credentials_object, run_unified_google_oauth, UNIFIED_GOOGLE_SCOPES


class GoogleCalendarIntegration(BaseIntegration):
    """Google Calendar — list events, schedule meetings, search, and delete events."""
    
    INTEGRATION_ID = "google_calendar"
    DISPLAY_NAME = "Google Calendar"
    DESCRIPTION = "Access, schedule, and manage Google Calendar events"
    AUTH_TYPE = AuthType.OAUTH2
    REQUIRED_PERMISSIONS = [Permission.INTEGRATION_CONNECT, Permission.NETWORK_ACCESS]
    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    def _get_calendar_service(self):
        from googleapiclient.discovery import build
        creds = build_google_credentials_object(self.credentials, scopes=UNIFIED_GOOGLE_SCOPES)
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    
    async def authenticate(self, params: dict[str, Any]) -> bool:
        oauth_creds = await run_unified_google_oauth(params, scopes=UNIFIED_GOOGLE_SCOPES)
        if oauth_creds:
            oauth_creds.integration_id = self.INTEGRATION_ID
            self.credentials = oauth_creds
            return True
        if self.credentials and self.credentials.access_token:
            return True
        return False
    
    async def test_connection(self) -> bool:
        if not self.credentials or not self.credentials.access_token:
            return False
        try:
            loop = asyncio.get_running_loop()
            def _test():
                service = self._get_calendar_service()
                service.calendarList().list(maxResults=1).execute()
                return True
            return await loop.run_in_executor(None, _test)
        except Exception as e:
            logger.error(f"Google Calendar test_connection failed: {e}")
            return False
    
    async def sync(self) -> dict[str, Any]:
        events = await self.list_events(days=7, max_results=20)
        self.last_sync = datetime.now()
        return {
            "events_synced": len(events),
            "upcoming": len(events),
            "sample": events[:5],
            "synced_at": datetime.now().isoformat(),
        }

    async def list_events(self, days: int = 7, query: str = "", max_results: int = 15) -> list[dict[str, Any]]:
        if not self.credentials:
            return []
        loop = asyncio.get_running_loop()
        def _list():
            service = self._get_calendar_service()
            now_utc = datetime.now(timezone.utc)
            time_min = now_utc.isoformat()
            time_max = (now_utc + timedelta(days=max(1, int(days)))).isoformat()
            kwargs: dict[str, Any] = {
                "calendarId": "primary",
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": max(1, min(int(max_results), 50)),
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if query:
                kwargs["q"] = query
            res = service.events().list(**kwargs).execute()
            items = res.get("items", [])
            formatted = []
            for ev in items:
                formatted.append({
                    "id": ev.get("id", ""),
                    "title": ev.get("summary", "(No Title)"),
                    "start": ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", ""),
                    "end": ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date", ""),
                    "location": ev.get("location", ""),
                    "description": ev.get("description", ""),
                    "htmlLink": ev.get("htmlLink", ""),
                    "attendees": [a.get("email", "") for a in ev.get("attendees", [])],
                })
            return formatted
        return await loop.run_in_executor(None, _list)

    async def create_event(
        self,
        title: str,
        start: str,
        end: str = "",
        description: str = "",
        location: str = "",
        attendees: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}
        if not end:
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end = (start_dt + timedelta(hours=1)).isoformat()
            except Exception:
                end = start

        # Resolve attendee names via SocialIntelligenceEngine if needed
        resolved_attendees = []
        for att in (attendees or []):
            att_str = str(att).strip()
            if not att_str:
                continue
            if "@" not in att_str:
                try:
                    from server.knowledge.social_intelligence import SocialIntelligenceEngine
                    dossier = SocialIntelligenceEngine().resolve_person(att_str)
                    if dossier and dossier.email:
                        att_str = dossier.email
                except Exception:
                    pass
            if "@" in att_str:
                resolved_attendees.append({"email": att_str})

        loop = asyncio.get_running_loop()
        def _create():
            service = self._get_calendar_service()
            local_tz = str(datetime.now().astimezone().tzinfo or "UTC")
            event_body: dict[str, Any] = {
                "summary": title,
                "description": description,
                "location": location,
                "start": {"dateTime": start, "timeZone": local_tz} if "T" in start else {"date": start},
                "end": {"dateTime": end, "timeZone": local_tz} if "T" in end else {"date": end},
            }
            if resolved_attendees:
                event_body["attendees"] = resolved_attendees
            created = service.events().insert(calendarId="primary", body=event_body).execute()
            return {
                "success": True,
                "id": created.get("id", ""),
                "title": created.get("summary", title),
                "start": created.get("start", {}),
                "end": created.get("end", {}),
                "htmlLink": created.get("htmlLink", ""),
            }
        return await loop.run_in_executor(None, _create)

    async def delete_event(self, event_id: str) -> dict[str, Any]:
        if not self.credentials:
            return {"success": False, "error": "Not authenticated"}
        loop = asyncio.get_running_loop()
        def _delete():
            service = self._get_calendar_service()
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            return {"success": True, "deleted_event_id": event_id}
        return await loop.run_in_executor(None, _delete)
    
    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "calendar_events",
                "description": "Get upcoming Google Calendar events or search events by keyword",
                "parameters": {
                    "days": {"type": "integer", "description": "Days to look ahead (default 7)"},
                    "query": {"type": "string", "description": "Optional search keyword"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "calendar_create",
                "description": "Schedule a new event or meeting on Google Calendar",
                "parameters": {
                    "title": {"type": "string", "description": "Event title"},
                    "start": {"type": "string", "description": "Start time in ISO 8601 format (e.g. 2026-11-04T15:00:00+05:30)"},
                    "end": {"type": "string", "description": "End time in ISO 8601 format (optional, defaults to +1 hour)"},
                    "description": {"type": "string", "description": "Optional event description or agenda"},
                    "location": {"type": "string", "description": "Optional location or meeting link"},
                    "attendees": {"type": "array", "description": "Optional list of attendee emails or contact names"},
                },
                "integration": self.INTEGRATION_ID,
            },
            {
                "name": "calendar_delete",
                "description": "Delete/cancel a Google Calendar event by event ID",
                "parameters": {
                    "event_id": {"type": "string", "description": "Google Calendar event ID"},
                },
                "integration": self.INTEGRATION_ID,
            },
        ]
