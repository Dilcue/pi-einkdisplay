#!/usr/bin/env python3
"""
simulate.py — render all pages to PNG files for visual inspection.

Usage:
    EINK_SIMULATE=1 python3 simulate.py

Output:
    docs/screenshots/dashboard.png
    docs/screenshots/cat.png
"""
import io
import os
import pathlib

import requests

os.environ["EINK_SIMULATE"] = "1"

from PIL import Image, ImageDraw

from pages.base import AppData, WHITE
from pages.header import render_header
from pages.dashboard import DashboardPage
from data.weather import WeatherReport, DayForecast
from data.calendar_client import CalendarEvent
from data.cat_client import _to_bwr

OUT_DIR = pathlib.Path(__file__).parent / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# The physical UC8179 ink renders red as a deep maroon rather than pure (255,0,0).
# Remap red pixels before saving PNGs so screenshots are visually representative.
_SIM_RED = (128, 0, 0)


def _remap_red(img: Image.Image) -> Image.Image:
    """Replace pure (255,0,0) pixels with the physical display maroon colour."""
    data = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            if data[x, y] == (255, 0, 0):
                data[x, y] = _SIM_RED
    return img


def _stub_weather() -> WeatherReport:
    d = DayForecast
    return WeatherReport(
        current_temp="52",
        current_cond="Partly Cloudy",
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
        CalendarEvent(summary="Family Dinner", time_display="Apr 4 (All Day)"),
    ]


_CAT_URL = "https://cdn2.thecatapi.com/images/TGuAku7fM.jpg"


def _stub_cat() -> Image.Image:
    """Fetch the sample Abyssinian cat and convert to BWR.
    Falls back to TheCatAPI random cat if the pinned URL is unreachable.
    """
    from data.cat_client import fetch as _fetch_random
    for url in [_CAT_URL, None]:
        try:
            if url is None:
                return _fetch_random()
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
            img.load()
            return _to_bwr(img)
        except Exception:
            continue
    raise RuntimeError("Could not fetch cat image for simulation")


if __name__ == "__main__":
    # --- Dashboard ---
    weather = _stub_weather()
    events = _stub_events()
    data = AppData(weather=weather, calendar_events=events)

    image = Image.new("RGB", (800, 480), WHITE)
    draw = ImageDraw.Draw(image)
    render_header(draw, data)
    DashboardPage().render(draw, data)
    out = OUT_DIR / "dashboard.png"
    _remap_red(image).save(str(out))
    print(f"Saved {out}")

    # --- Cat mode ---
    cat_img = _stub_cat()
    out = OUT_DIR / "cat.png"
    _remap_red(cat_img).save(str(out))
    print(f"Saved {out}")
