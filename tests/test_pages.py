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
        current_temp="52", current_cond="Clear",
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
