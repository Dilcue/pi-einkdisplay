# tests/test_calendar_format.py
"""Tests for _format_event — pure formatting logic, no network calls."""
import pytest
from data.calendar_client import _format_event


def _make_event(start_dt, end_dt, summary="Test Event", is_all_day=False):
    if is_all_day:
        return {
            "summary": summary,
            "start": {"date": start_dt},
            "end": {"date": end_dt},
        }
    return {
        "summary": summary,
        "start": {"dateTime": start_dt},
        "end": {"dateTime": end_dt},
    }


def test_single_day_all_day():
    event = _make_event("2026-04-05", "2026-04-06", is_all_day=True)
    result = _format_event(event)
    assert result.summary == "Test Event"
    assert "(All Day)" in result.time_display
    assert "Sun" in result.time_display
    assert "Apr" in result.time_display


def test_multi_day_all_day_range():
    event = _make_event("2026-04-06", "2026-04-14", is_all_day=True)
    result = _format_event(event)
    assert result.time_display.startswith("Mon")   # Apr 6 is Monday
    assert result.time_display.endswith("Mon Apr 13") or "Mon Apr 13" in result.time_display
    assert " - " in result.time_display
    assert "(All Day)" not in result.time_display


def test_timed_same_day():
    event = _make_event("2026-04-05T09:00:00-04:00", "2026-04-05T10:00:00-04:00")
    result = _format_event(event)
    assert "9:00" in result.time_display
    assert "10:00" in result.time_display


def test_no_summary_fallback():
    event = {"start": {"date": "2026-04-05"}, "end": {"date": "2026-04-06"}}
    result = _format_event(event)
    assert result.summary == "(No title)"


def test_zero_duration_timed_event():
    # start == end treated as point-in-time — full date+time format
    event = _make_event("2026-04-05T09:00:00-04:00", "2026-04-05T09:00:00-04:00")
    result = _format_event(event)
    assert "9:00" in result.time_display
    assert "AM" in result.time_display


def test_multi_day_timed_event():
    event = _make_event("2026-04-05T22:00:00-04:00", "2026-04-06T06:00:00-04:00")
    result = _format_event(event)
    # Use day-of-week names — consistent across platforms unlike %-d zero-padding
    assert "Sun" in result.time_display
    assert "Mon" in result.time_display
    assert "Apr" in result.time_display


def test_format_event_raises_on_missing_date_fields():
    """An event with an empty start dict raises rather than silently returning garbage."""
    event = {"summary": "Bad Event", "start": {}, "end": {}}
    with pytest.raises((TypeError, ValueError)):
        _format_event(event)
