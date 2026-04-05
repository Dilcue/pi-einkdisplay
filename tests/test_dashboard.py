# tests/test_dashboard.py
import os
os.environ["EINK_SIMULATE"] = "1"

from PIL import Image, ImageDraw
from pages.base import AppData, WHITE
from pages.header import render_header
from pages.dashboard import DashboardPage
from data.weather import WeatherReport, DayForecast
from data.calendar_client import CalendarEvent


def _make_draw():
    image = Image.new("RGB", (800, 480), WHITE)
    return image, ImageDraw.Draw(image)


def _stub_day():
    return DayForecast(day="Mon", temp="52/40", cond="Clear", icon="H")


def _stub_weather():
    return WeatherReport(
        current_temp="52", current_cond="Clear",
        current_feels_like="48", current_icon="H",
        today=_stub_day(), tomorrow=_stub_day(),
        day3=_stub_day(), day4=_stub_day(), day5=_stub_day(),
    )


def _stub_events():
    return [
        CalendarEvent(summary="Team Standup", time_display="9:00 AM"),
        CalendarEvent(summary="Lunch", time_display="12:30 PM"),
        CalendarEvent(summary="Sprint Review", time_display="Wed Apr 2, 2:00 PM"),
        CalendarEvent(summary="Doctor", time_display="Thu Apr 3, 10:00 AM"),
        CalendarEvent(summary="Family Dinner", time_display="Apr 4 (All Day)"),
    ]


def test_dashboard_render_full():
    _, draw = _make_draw()
    data = AppData(weather=_stub_weather(), calendar_events=_stub_events())
    DashboardPage().render(draw, data)


def test_dashboard_render_no_weather():
    _, draw = _make_draw()
    data = AppData(weather=None, calendar_events=_stub_events())
    DashboardPage().render(draw, data)


def test_dashboard_render_no_events():
    _, draw = _make_draw()
    data = AppData(weather=_stub_weather(), calendar_events=[])
    DashboardPage().render(draw, data)


def test_dashboard_render_partial_events():
    _, draw = _make_draw()
    data = AppData(weather=_stub_weather(), calendar_events=_stub_events()[:2])
    DashboardPage().render(draw, data)


def test_dashboard_render_no_data():
    _, draw = _make_draw()
    DashboardPage().render(draw, AppData())
