# main.py
from __future__ import annotations

import logging
import pathlib
import threading
import time

from PIL import Image
from PIL import ImageFont

import buttons
import display
from config import settings
from data import calendar_client
from data import cat_client
from data import weather
from pages.base import AppData
from pages.dashboard import DashboardPage
from pages.header import render_header

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
_log = logging.getLogger(__name__)

_SW1 = 5
_SW2 = 6
_CAT_TIMEOUT = 60.0
_FONTS_DIR = pathlib.Path(__file__).parent / "fonts"


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


def _show_no_cats() -> None:
    """Display 'No cats available' error and hold for 3 seconds."""
    image, draw = display.new_image()
    try:
        font = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 16)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 20), "No cats available", font=font, fill=(255, 0, 0))
    display.update(image)
    time.sleep(3)


def _prefetch_cat(holder: list, lock: threading.Lock, cancelled: list) -> None:
    """Fetch and convert next cat image; store result in holder under lock."""
    try:
        img = cat_client.fetch()
        with lock:
            if not cancelled:
                holder.clear()
                holder.append(img)
                _log.info("Cat pre-fetch complete")
    except Exception as e:
        _log.warning("Cat pre-fetch failed: %s", e)


def _start_prefetch() -> tuple[list, threading.Lock, list]:
    """Start a background cat pre-fetch; return (holder, lock, cancelled_flag)."""
    holder: list = []
    lock = threading.Lock()
    cancelled: list = []
    threading.Thread(target=_prefetch_cat, args=(holder, lock, cancelled), daemon=True).start()
    return holder, lock, cancelled


def _get_cat(holder: list, lock: threading.Lock) -> Image.Image:
    """Return pre-fetched image if ready, else fetch live."""
    with lock:
        if holder:
            return holder[0]
    _log.info("Pre-fetch not ready — fetching live")
    return cat_client.fetch()


def cat_mode() -> None:
    """Full-screen cat mode. Returns when SW2 pressed or timeout."""
    _log.info("Entering cat mode")
    try:
        img = cat_client.fetch()
    except RuntimeError as e:
        _log.error("Cat fetch failed: %s", e)
        _show_no_cats()
        return

    display.update(img)
    holder, lock, cancelled = _start_prefetch()

    while True:
        pin = buttons.wait_for_button(_CAT_TIMEOUT)
        if pin == _SW1:
            try:
                img = _get_cat(holder, lock)
            except RuntimeError as e:
                _log.error("Cat fetch failed: %s", e)
                _show_no_cats()
                return
            display.update(img)
            cancelled.append(True)  # cancel old pre-fetch thread
            holder, lock, cancelled = _start_prefetch()
        else:
            # SW2 or timeout — exit cat mode
            _log.info("Exiting cat mode (pin=%s)", pin)
            return


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
            cat_mode()
            last_fp = None  # force dashboard re-render on return


if __name__ == "__main__":
    main()
