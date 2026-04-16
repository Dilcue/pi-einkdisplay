# main.py
from __future__ import annotations

import logging
import time

import buttons
import display
from config import settings
from data import calendar_client
from data import weather
from pages.base import AppData
from cat_mode import CatMode
from pages.dashboard import DashboardPage
from pages.header import render_header

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
_log = logging.getLogger(__name__)

_SW1 = 6 if settings.swap_buttons else 5
_SW2 = 5 if settings.swap_buttons else 6


def _refresh_weather(app_data: AppData) -> None:
    try:
        app_data.weather = weather.fetch()
        _log.info("Weather updated")
    except Exception as e:
        _log.error("Weather fetch failed: %s", e)


def _refresh_calendar(app_data: AppData) -> None:
    try:
        app_data.calendar_events = calendar_client.fetch()
        _log.info("Calendar updated (%d events)", len(app_data.calendar_events))
    except Exception as e:
        _log.error("Calendar fetch failed: %s", e)


def _fingerprint(app_data: AppData) -> str:
    """Returns a string that changes when calendar or weather data changes."""
    w = app_data.weather
    w_part = f"{w.current_temp}|{w.current_cond}|{w.current_feels_like}|{w.today.temp}|{w.tomorrow.temp}|{w.day3.temp}|{w.day4.temp}|{w.day5.temp}" if w else ""
    events = app_data.calendar_events or []
    e_part = "|".join(f"{e.summary}~{e.time_display}" for e in events[:5])
    return f"{w_part}#{e_part}"


def main() -> None:
    refresh_interval = settings.data_refresh_minutes * 60

    display.init()
    buttons.init()
    display.splash()

    app_data = AppData()
    _refresh_weather(app_data)
    _refresh_calendar(app_data)

    last_refresh = time.time()
    last_fp = None
    page = DashboardPage()
    cat = CatMode()

    while True:
        now = time.time()
        if now - last_refresh >= refresh_interval:
            _refresh_weather(app_data)
            _refresh_calendar(app_data)
            last_refresh = now

        fp = _fingerprint(app_data)
        if fp != last_fp:
            image, draw = display.new_image()
            render_header(draw, app_data)
            page.render(draw, app_data)
            display.update(image)
            last_fp = fp
            _log.info("Display refreshed (data changed)")

        pin = buttons.wait_for_button(refresh_interval)
        if pin == _SW1:
            cat.enter(_SW1, _SW2)
            last_fp = None  # force dashboard re-render on return


if __name__ == "__main__":
    main()
