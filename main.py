import logging
import time

import buttons
import display
from config import settings
from data import weather
from data import calendar_client
from pages.base import AppData
from pages.clock import ClockPage
from pages.weather_current import WeatherCurrentPage
from pages.weather_forecast import WeatherForecastPage
from pages.calendar_page import CalendarPage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
_log = logging.getLogger(__name__)

_PAGE_REGISTRY = {
    "clock": ClockPage,
    "weather_current": WeatherCurrentPage,
    "weather_forecast": WeatherForecastPage,
    "calendar": CalendarPage,
}

pages = [_PAGE_REGISTRY[p]() for p in settings.pages if p in _PAGE_REGISTRY]

_refresh_interval = settings.data_refresh_minutes * 60


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
    display.init()
    buttons.init()

    app_data = AppData()
    _refresh_weather(app_data)
    _refresh_calendar(app_data)

    last_refresh = time.time()
    page_index = 0

    while True:
        now = time.time()
        if now - last_refresh >= _refresh_interval:
            _refresh_weather(app_data)
            _refresh_calendar(app_data)
            last_refresh = now

        image, draw = display.new_image()
        page = pages[page_index]
        page.render(draw, app_data)
        display.update(image)

        buttons.wait_or_advance(settings.page_delay_seconds + page.time_bonus)
        page_index = (page_index + 1) % len(pages)

        if page_index == 0:
            display.clear()


if __name__ == "__main__":
    main()
