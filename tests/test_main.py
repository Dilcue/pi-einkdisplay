# tests/test_main.py
import os
import queue
import sys
import threading
from unittest.mock import MagicMock, patch

from PIL import Image

os.environ["EINK_SIMULATE"] = "1"

sys.modules['gpiod'] = MagicMock()
sys.modules['gpiod.line'] = MagicMock()


def test_main_module_imports():
    import main
    assert hasattr(main, "DashboardPage")
    assert callable(main._fingerprint)


def _make_cat_image():
    return Image.new("RGB", (800, 480), (255, 0, 0))


def test_cat_mode_displays_cat_and_returns_on_sw2(monkeypatch):
    import main
    import buttons
    from cat_mode import CatMode

    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)

    import cat_mode as cat_mod
    monkeypatch.setattr(cat_mod, "display", MagicMock())

    q.put(main._SW2)

    with patch("cat_mode.cat_client.fetch", return_value=_make_cat_image()):
        cat = CatMode()
        cat._start_prefetch = lambda: ([], threading.Lock(), [])
        cat.enter(main._SW1, main._SW2)

    cat_mod.display.update.assert_called_once()


def test_cat_mode_shows_new_cat_on_sw1(monkeypatch):
    import main
    import buttons
    from cat_mode import CatMode

    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)

    import cat_mode as cat_mod
    monkeypatch.setattr(cat_mod, "display", MagicMock())

    q.put(main._SW1)
    q.put(main._SW2)

    with patch("cat_mode.cat_client.fetch", return_value=_make_cat_image()):
        cat = CatMode()
        cat._start_prefetch = lambda: ([], threading.Lock(), [])
        cat.enter(main._SW1, main._SW2)

    assert cat_mod.display.update.call_count == 2


def test_cat_mode_shows_error_and_returns_on_fetch_failure(monkeypatch):
    import main
    import buttons
    from cat_mode import CatMode

    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)

    import cat_mode as cat_mod
    mock_display = MagicMock()
    mock_display.new_image.return_value = (MagicMock(), MagicMock())
    monkeypatch.setattr(cat_mod, "display", mock_display)
    monkeypatch.setattr(cat_mod.time, "sleep", MagicMock())

    with patch("cat_mode.cat_client.fetch", side_effect=RuntimeError("no cats")):
        cat = CatMode()
        cat.enter(main._SW1, main._SW2)

    mock_display.update.assert_called_once()


def test_refresh_weather_preserves_stale_data_on_failure():
    import main
    from pages.base import AppData
    from data.weather import WeatherReport, DayForecast

    stub_day = DayForecast(day="Mon", temp="50/40", cond="Clear", icon="H")
    app_data = AppData()
    app_data.weather = WeatherReport(
        current_temp="52", current_cond="Clear", current_feels_like="48",
        current_icon="H", today=stub_day, tomorrow=stub_day,
        day3=stub_day, day4=stub_day, day5=stub_day,
    )
    original = app_data.weather

    with patch("main.weather.fetch", side_effect=RuntimeError("network error")):
        main._refresh_weather(app_data)

    assert app_data.weather is original


def test_refresh_calendar_preserves_stale_data_on_failure():
    import main
    from pages.base import AppData
    from data.calendar_client import CalendarEvent

    app_data = AppData()
    app_data.calendar_events = [CalendarEvent(summary="Test", time_display="9:00 AM")]
    original = app_data.calendar_events

    with patch("main.calendar_client.fetch", side_effect=RuntimeError("network error")):
        main._refresh_calendar(app_data)

    assert app_data.calendar_events is original


def test_cat_mode_returns_on_timeout(monkeypatch):
    import main
    import buttons
    from cat_mode import CatMode

    q = queue.Queue()
    monkeypatch.setattr(buttons, "_press_queue", q)

    import cat_mode as cat_mod
    monkeypatch.setattr(cat_mod, "display", MagicMock())

    with patch("cat_mode.cat_client.fetch", return_value=_make_cat_image()):
        with patch("buttons.wait_for_button", side_effect=[None]):
            cat = CatMode()
            cat.enter(main._SW1, main._SW2)

    cat_mod.display.update.assert_called_once()
