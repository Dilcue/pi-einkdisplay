# main.py
import logging
import time

import buttons
import display
from config import settings
from data import weather
from data import calendar_client
from data import cats
from data import spotify as spotify_module
from pages.base import AppData
from pages.header import render_header
from pages.clock import ClockPage
from pages.weather_body import WeatherBodyPage
from pages.calendar_page import CalendarPage
from pages.cats import CatsPage
from pages.spotify_page import SpotifyPage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
_log = logging.getLogger(__name__)

_PAGE_REGISTRY = {
    "clock": ClockPage,
    "weather": WeatherBodyPage,
    "calendar": CalendarPage,
    "cats": CatsPage,
    "spotify": SpotifyPage,
}


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


def _refresh_cats(app_data: AppData) -> None:
    if not settings.cats_enabled:
        return
    try:
        app_data.cats = cats.fetch(settings.cat_cache_size)
        app_data.cat_index = 0
        _log.info("Cats updated (%d frames)", len(app_data.cats))
    except Exception as e:
        _log.error("Cat fetch failed: %s", e)


def _refresh_spotify(app_data: AppData) -> None:
    if not settings.spotify_enabled:
        return
    try:
        app_data.spotify = spotify_module.fetch()
        _log.info("Spotify updated (playing=%s)", app_data.spotify.playing)
    except Exception as e:
        _log.error("Spotify fetch failed: %s", e)


def main() -> None:
    try:
        pages = [_PAGE_REGISTRY[p]() for p in settings.pages if p in _PAGE_REGISTRY]
        if not pages:
            _log.error("No valid pages configured — check 'pages' in config.json")
            return
    except Exception as e:
        _log.error("Failed to initialize pages: %s", e)
        return

    refresh_interval = settings.data_refresh_minutes * 60

    display.init()
    buttons.init()
    display.splash()

    app_data = AppData()
    app_data.total_body_pages = len(pages)
    _refresh_weather(app_data)
    _refresh_calendar(app_data)
    _refresh_cats(app_data)
    _refresh_spotify(app_data)

    last_refresh = time.time()
    page_index = 0

    while True:
        now = time.time()
        if now - last_refresh >= refresh_interval:
            _refresh_weather(app_data)
            _refresh_calendar(app_data)
            _refresh_cats(app_data)
            _refresh_spotify(app_data)
            last_refresh = now

        app_data.body_page_index = page_index

        image, draw = display.new_image()
        render_header(draw, app_data)
        pages[page_index].render(draw, app_data)
        # Spotify needs per-cycle refresh when active (track progress changes)
        if isinstance(pages[page_index], SpotifyPage) and settings.spotify_enabled:
            _refresh_spotify(app_data)
        # No display.clear() needed — UC8179 driver performs a full refresh on each display() call
        display.update(image)

        buttons.wait_or_advance(settings.page_delay_seconds + pages[page_index].time_bonus)
        page_index = (page_index + 1) % len(pages)
        app_data.cat_index += 1


if __name__ == "__main__":
    main()
