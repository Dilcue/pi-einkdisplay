# tests/test_weather.py
import time as _time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from data.weather import WeatherReport, DayForecast


def _stub_day():
    return DayForecast(day="Mon", temp="50/40", cond="Clear", icon="H")


def test_weather_report_has_day4_and_day5():
    w = WeatherReport(
        current_temp="52",
        current_cond="Clear",
        current_feels_like="48",
        current_icon="H",
        today=_stub_day(),
        tomorrow=_stub_day(),
        day3=_stub_day(),
        day4=_stub_day(),
        day5=_stub_day(),
    )
    assert w.day4.day == "Mon"
    assert w.day5.day == "Mon"


def _make_response(data):
    m = MagicMock()
    m.raise_for_status = MagicMock()
    m.json.return_value = data
    return m


@patch("data.weather.requests.get")
def test_fetch_uses_fallback_for_missing_forecast_days(mock_get):
    """When OWM returns fewer than 5 future days, missing days use the --- fallback."""
    now_ts = int(_time.time())
    current_data = {
        "weather": [{"icon": "01d", "main": "Clear"}],
        "main": {"temp": 52.0, "feels_like": 48.0},
        "sys": {"sunrise": now_ts - 3600, "sunset": now_ts + 3600},
    }
    now_utc = datetime.now(tz=timezone.utc)
    periods = [
        {
            "dt": int((now_utc + timedelta(days=i)).replace(hour=12, minute=0, second=0, microsecond=0).timestamp()),
            "weather": [{"icon": "01d", "main": "Clear"}],
            "main": {"temp": 52.0, "temp_max": 55.0, "temp_min": 45.0},
        }
        for i in range(2)  # only 2 future days
    ]
    mock_get.side_effect = [
        _make_response(current_data),
        _make_response({"list": periods}),
    ]

    from data.weather import fetch
    result = fetch()
    assert result.day3.day == "---"
    assert result.day4.day == "---"
    assert result.day5.day == "---"
