#!/usr/bin/env python3
"""
simulate.py — render all pages to PNG files for visual inspection.

Usage:
    EINK_SIMULATE=1 python3 simulate.py

Output: /tmp/einkdisplay/clock.png, weather.png, calendar.png
"""
import os
import pathlib

os.environ["EINK_SIMULATE"] = "1"

from PIL import Image, ImageDraw

import display
from pages.base import AppData, WHITE
from pages.header import render_header
from pages.clock import ClockPage
from pages.weather_body import WeatherBodyPage
from pages.calendar_page import CalendarPage
from data.weather import WeatherReport, DayForecast
from data.calendar_client import CalendarEvent

OUT_DIR = pathlib.Path("/tmp/einkdisplay")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _stub_weather() -> WeatherReport:
    d = DayForecast
    return WeatherReport(
        last_update="9:41",
        current_temp="52",
        current_cond="Partly Cloudy",
        current_desc="partly cloudy",
        current_wind_speed="12",
        current_wind_dir="NW",
        current_visibility="10000",
        current_sunrise="6:28 AM",
        current_sunset="7:52 PM",
        current_feels_like="46",
        current_icon="E",
        today=d(day="Tue", temp="52/38", cond="Cloudy", icon="D"),
        tomorrow=d(day="Wed", temp="58/44", cond="Rain", icon="B"),
        day3=d(day="Thu", temp="61/48", cond="Clear", icon="H"),
        day4=d(day="Fri", temp="55/40", cond="Snow", icon="C"),
        day5=d(day="Sat", temp="47/35", cond="Cloudy", icon="D"),
    )


def _stub_events() -> list:
    return [
        CalendarEvent(summary="Team Standup", time_display="9:00 AM"),
        CalendarEvent(summary="Lunch with Sarah", time_display="12:30 PM"),
        CalendarEvent(summary="Sprint Review", time_display="Wed Apr 2, 2:00 PM"),
        CalendarEvent(summary="Doctor Appointment", time_display="Thu Apr 3, 10:00 AM"),
        CalendarEvent(summary="Family Dinner", time_display="Fri Apr 4 (All Day)"),
    ]


def render_page(name: str, page, data: AppData) -> None:
    image = Image.new("RGB", (800, 480), WHITE)
    draw = ImageDraw.Draw(image)
    render_header(draw, data)
    page.render(draw, data)
    out = OUT_DIR / f"{name}.png"
    image.save(str(out))
    print(f"  Saved {out}")


if __name__ == "__main__":
    weather = _stub_weather()
    events = _stub_events()

    pages = [
        ("calendar", CalendarPage(), AppData(weather=weather, calendar_events=events, body_page_index=0, total_body_pages=3)),
        ("weather", WeatherBodyPage(), AppData(weather=weather, calendar_events=events, body_page_index=1, total_body_pages=3)),
        ("clock", ClockPage(), AppData(weather=weather, calendar_events=events, body_page_index=2, total_body_pages=3)),
    ]

    print(f"Rendering {len(pages)} pages to {OUT_DIR}/")
    for name, page, data in pages:
        render_page(name, page, data)
    print("Done. Open the PNGs to inspect layout.")
