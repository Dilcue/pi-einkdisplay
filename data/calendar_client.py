import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import dateutil.parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import settings

_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
_log = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    summary: str
    time_display: str


def _load_creds() -> Credentials | None:
    try:
        creds = Credentials.from_authorized_user_file(settings.token_path, _SCOPES)
    except FileNotFoundError:
        return None

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(settings.token_path, "w") as f:
                f.write(creds.to_json())
            return creds
        except Exception as e:
            _log.error("Token refresh failed: %s", e)
            return None

    # Refresh token missing or invalid — browser flow required (not possible headless)
    _log.error(
        "Google token is invalid and cannot be refreshed headlessly. "
        "Run auth setup manually to generate a new token.json."
    )
    return None


def _format_event(event: dict) -> CalendarEvent:
    summary = event.get("summary", "(No title)")
    all_day = event["start"].get("dateTime") is None

    start = dateutil.parser.parse(event["start"].get("dateTime") or event["start"].get("date"))
    end = dateutil.parser.parse(event["end"].get("dateTime") or event["end"].get("date"))

    if all_day:
        time_display = start.strftime("%a %b %d") + " (All Day)"
    elif start == end:
        time_display = start.strftime("%a %b %d, %I:%M %p")
    elif start.date() == end.date():
        time_display = start.strftime("%a %b %d, %I:%M") + "-" + end.strftime("%I:%M %p")
    else:
        time_display = start.strftime("%a %b %d, %I:%M") + "-" + end.strftime("%a %b %d, %I:%M %p")

    return CalendarEvent(summary=summary, time_display=time_display)


def fetch() -> list[CalendarEvent]:
    creds = _load_creds()
    if creds is None:
        raise RuntimeError("No valid Google credentials available")

    service = build("calendar", "v3", credentials=creds)
    now = datetime.now(tz=timezone.utc).isoformat()

    events = []
    for cal_id in settings.calendar_ids:
        result = service.events().list(
            calendarId=cal_id,
            timeMin=now,
            maxResults=settings.calendar_max_events,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events.extend(result.get("items", []))

    def _start_key(e: dict) -> str:
        return e["start"].get("dateTime") or e["start"].get("date") or ""

    events.sort(key=_start_key)
    return [_format_event(e) for e in events[:settings.calendar_max_events]]
