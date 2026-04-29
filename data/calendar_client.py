from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import dateutil.parser
from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import settings

_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
_log = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    summary: str
    time_display: str


def _load_creds() -> service_account.Credentials | None:
    try:
        return service_account.Credentials.from_service_account_file(
            settings.service_account_path, scopes=_SCOPES
        )
    except FileNotFoundError:
        _log.error("service_account.json not found at %s", settings.service_account_path)
        return None
    except Exception as e:
        _log.error("Failed to load service account credentials: %s", e)
        return None


def _format_event(event: dict) -> CalendarEvent:
    summary = event.get("summary", "(No title)")
    all_day = event["start"].get("dateTime") is None

    start = dateutil.parser.parse(event["start"].get("dateTime") or event["start"].get("date"))
    end = dateutil.parser.parse(event["end"].get("dateTime") or event["end"].get("date"))

    if all_day:
        end_display = end - timedelta(days=1)  # Google end date is exclusive
        if end_display.date() == start.date():
            time_display = start.strftime("%a %b %-d") + " (All Day)"
        else:
            time_display = start.strftime("%a %b %-d") + " - " + end_display.strftime("%a %b %-d")
    elif start == end:
        time_display = start.strftime("%a %b %d, %-I:%M %p")
    elif start.date() == end.date():
        time_display = start.strftime("%a %b %d, %-I:%M") + "-" + end.strftime("%-I:%M %p")
    else:
        time_display = start.strftime("%a %b %d, %-I:%M") + "-" + end.strftime("%a %b %d, %-I:%M %p")

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
            maxResults=settings.calendar_max_events * max(1, len(settings.calendar_ids)),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events.extend(result.get("items", []))

    def _start_key(e: dict) -> str:
        return e["start"].get("dateTime") or e["start"].get("date") or ""

    events.sort(key=_start_key)
    formatted = []
    for e in events[:settings.calendar_max_events]:
        try:
            formatted.append(_format_event(e))
        except Exception:
            _log.warning("Skipping malformed calendar event: %s", e.get("summary", "(unknown)"))
    return formatted
