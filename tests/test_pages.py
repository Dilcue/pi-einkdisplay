# tests/test_pages.py
import os
os.environ["EINK_SIMULATE"] = "1"

from PIL import Image, ImageDraw
from pages.base import AppData, WHITE
from pages.header import render_header
from data.weather import WeatherReport, DayForecast


def _make_draw():
    image = Image.new("RGB", (800, 480), WHITE)
    return image, ImageDraw.Draw(image)


def _stub_weather():
    d = DayForecast("Mon", "52/40", "Clear", "H")
    return WeatherReport(
        last_update="9:00", current_temp="52", current_cond="Clear",
        current_desc="clear sky", current_wind_speed="5", current_wind_dir="NW",
        current_visibility="10000", current_sunrise="6:30 AM", current_sunset="7:45 PM",
        current_feels_like="48", current_icon="H",
        today=d, tomorrow=d, day3=d, day4=d, day5=d,
    )


def test_render_header_no_crash():
    _, draw = _make_draw()
    data = AppData(weather=_stub_weather())
    render_header(draw, data)  # must not raise


def test_render_header_no_weather():
    _, draw = _make_draw()
    render_header(draw, AppData())  # weather=None, should not raise


from pages.clock import ClockPage


def test_clock_render_no_crash():
    _, draw = _make_draw()
    data = AppData()
    ClockPage().render(draw, data)


from pages.weather_body import WeatherBodyPage


def test_weather_body_render_no_crash():
    _, draw = _make_draw()
    data = AppData(weather=_stub_weather())
    WeatherBodyPage().render(draw, data)


def test_weather_body_render_no_weather():
    _, draw = _make_draw()
    WeatherBodyPage().render(draw, AppData())


from pages.calendar_page import CalendarPage
from data.calendar_client import CalendarEvent


def test_calendar_render_no_crash():
    _, draw = _make_draw()
    events = [CalendarEvent(summary="Team Standup", time_display="9:00 AM")]
    data = AppData(calendar_events=events)
    CalendarPage().render(draw, data)


def test_calendar_render_no_events():
    _, draw = _make_draw()
    CalendarPage().render(draw, AppData(calendar_events=[]))
