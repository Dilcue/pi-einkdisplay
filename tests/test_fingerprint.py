# tests/test_fingerprint.py
import os
os.environ["EINK_SIMULATE"] = "1"

import sys
from unittest.mock import MagicMock
sys.modules['gpiod'] = MagicMock()
sys.modules['gpiod.line'] = MagicMock()

import main
from pages.base import AppData
from data.weather import WeatherReport, DayForecast
from data.calendar_client import CalendarEvent


def _stub_day():
    return DayForecast(day="Mon", temp="52/40", cond="Clear", icon="H")


def _stub_weather(**overrides):
    fields = dict(
        current_temp="52", current_cond="Clear",
        current_feels_like="48", current_icon="H",
        today=_stub_day(), tomorrow=_stub_day(),
        day3=_stub_day(), day4=_stub_day(), day5=_stub_day(),
    )
    fields.update(overrides)
    return WeatherReport(**fields)


def test_fingerprint_no_data():
    fp = main._fingerprint(AppData())
    assert fp == "#"


def test_fingerprint_with_weather():
    data = AppData(weather=_stub_weather())
    fp = main._fingerprint(data)
    assert "52" in fp
    assert "Clear" in fp
    assert "48" in fp


def test_fingerprint_with_events():
    events = [CalendarEvent(summary="Standup", time_display="9:00 AM")]
    data = AppData(calendar_events=events)
    fp = main._fingerprint(data)
    assert "Standup" in fp
    assert "9:00 AM" in fp


def test_fingerprint_changes_on_temp_change():
    data1 = AppData(weather=_stub_weather(current_temp="52"))
    data2 = AppData(weather=_stub_weather(current_temp="60"))
    assert main._fingerprint(data1) != main._fingerprint(data2)


def test_fingerprint_changes_on_feels_like_change():
    data1 = AppData(weather=_stub_weather(current_feels_like="48"))
    data2 = AppData(weather=_stub_weather(current_feels_like="55"))
    assert main._fingerprint(data1) != main._fingerprint(data2)


def test_fingerprint_changes_on_event_change():
    e1 = [CalendarEvent(summary="Standup", time_display="9:00 AM")]
    e2 = [CalendarEvent(summary="All Hands", time_display="10:00 AM")]
    assert main._fingerprint(AppData(calendar_events=e1)) != main._fingerprint(AppData(calendar_events=e2))


def test_fingerprint_stable_same_data():
    data = AppData(weather=_stub_weather(), calendar_events=[
        CalendarEvent(summary="Standup", time_display="9:00 AM")
    ])
    assert main._fingerprint(data) == main._fingerprint(data)


def test_fingerprint_caps_events_at_five():
    events = [CalendarEvent(summary=f"Event {i}", time_display=f"{i}:00 AM") for i in range(10)]
    data_5 = AppData(calendar_events=events[:5])
    data_10 = AppData(calendar_events=events)
    # Events 6-10 should not affect the fingerprint
    assert main._fingerprint(data_5) == main._fingerprint(data_10)
