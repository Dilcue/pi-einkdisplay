# main.py
import logging
import time

import buttons
import display
from config import settings
from data import weather
from data import calendar_client
from pages.base import AppData
from pages.header import render_header
from pages.dashboard import DashboardPage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
_log = logging.getLogger(__name__)


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


def main() -> None:
    refresh_interval = settings.data_refresh_minutes * 60

    display.init()
    buttons.init()
    display.splash()

    app_data = AppData()
    _refresh_weather(app_data)
    _refresh_calendar(app_data)

    last_refresh = time.time()
    page = DashboardPage()

    while True:
        now = time.time()
        if now - last_refresh >= refresh_interval:
            _refresh_weather(app_data)
            _refresh_calendar(app_data)
            last_refresh = now

        image, draw = display.new_image()
        render_header(draw, app_data)
        page.render(draw, app_data)
        display.update(image)

        buttons.wait_or_advance(settings.page_delay_seconds)


if __name__ == "__main__":
    main()
