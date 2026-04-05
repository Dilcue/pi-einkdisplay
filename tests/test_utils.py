# tests/test_utils.py
from datetime import datetime, timezone
from utils import local_time, resolve_weather_icon


def test_local_time_with_tz():
    utc = datetime(2026, 4, 5, 12, 0, 0, tzinfo=timezone.utc)
    result = local_time(utc)
    assert result.tzinfo is not None
    assert result.utctimetuple() == utc.utctimetuple()


def test_local_time_without_tz_assumes_utc():
    naive = datetime(2026, 4, 5, 12, 0, 0)
    result = local_time(naive)
    assert result.tzinfo is not None


def test_resolve_weather_icon_clear_day():
    assert resolve_weather_icon("01d", is_day=True) == "H"


def test_resolve_weather_icon_clear_night():
    assert resolve_weather_icon("01n", is_day=False) == "J"


def test_resolve_weather_icon_few_clouds_day():
    assert resolve_weather_icon("02d", is_day=True) == "E"
    assert resolve_weather_icon("04d", is_day=True) == "E"


def test_resolve_weather_icon_few_clouds_night():
    assert resolve_weather_icon("02n", is_day=False) == "D"


def test_resolve_weather_icon_scattered_clouds():
    assert resolve_weather_icon("03d", is_day=True) == "D"
    assert resolve_weather_icon("03n", is_day=False) == "D"


def test_resolve_weather_icon_rain():
    assert resolve_weather_icon("09d", is_day=True) == "B"
    assert resolve_weather_icon("10d", is_day=True) == "B"


def test_resolve_weather_icon_thunderstorm():
    assert resolve_weather_icon("11d", is_day=True) == "F"


def test_resolve_weather_icon_snow():
    assert resolve_weather_icon("13d", is_day=True) == "C"


def test_resolve_weather_icon_mist():
    assert resolve_weather_icon("50d", is_day=True) == "G"


def test_resolve_weather_icon_unknown():
    assert resolve_weather_icon("99d", is_day=True) == ""
