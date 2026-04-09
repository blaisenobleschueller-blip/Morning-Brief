from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

from morning_brief.config import Config
from morning_brief.fetchers.base import BaseFetcher, FetchResult

_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarFetcher(BaseFetcher):
    def __init__(self, config: Config) -> None:
        self._config = config

    def fetch(self) -> FetchResult:
        try:
            creds = self._get_credentials()
            from googleapiclient.discovery import build
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            events = self._fetch_today(service)
            content = self._format(events)
            return FetchResult(source_name="Calendar", content=content, success=True)
        except Exception as e:
            return FetchResult(source_name="Calendar", content="", success=False, error=str(e))

    def _get_credentials(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        token_file = self._config.google_token_file
        creds_file = self._config.google_credentials_file

        creds = None
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, _SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_file):
                    raise FileNotFoundError(
                        f"Google OAuth credentials not found at {creds_file}. "
                        "Download from Google Cloud Console and place there."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, _SCOPES)
                creds = flow.run_local_server(port=0)
            # Save token for next run
            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            with open(token_file, "w") as f:
                f.write(creds.to_json())

        return creds

    def _fetch_today(self, service) -> list[dict]:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_of_day.isoformat(),
                timeMax=end_of_day.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return result.get("items", [])

    def _format(self, events: list[dict]) -> str:
        if not events:
            return "Calendar: No events today"
        lines = ["Today's Calendar:"]
        for event in events:
            summary = event.get("summary", "Untitled")
            start = event.get("start", {})
            if "dateTime" in start:
                dt = datetime.fromisoformat(start["dateTime"])
                time_str = dt.strftime("%-I:%M %p")
                lines.append(f"  {time_str} - {summary}")
            else:
                lines.append(f"  All day: {summary}")
        return "\n".join(lines)
