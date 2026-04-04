# tests/test_weather.py
from data.weather import WeatherReport, DayForecast


def _stub_day():
    return DayForecast(day="Mon", temp="50/40", cond="Clear", icon="H")


def test_weather_report_has_day4_and_day5():
    w = WeatherReport(
        last_update="9:00",
        current_temp="52",
        current_cond="Clear",
        current_desc="clear sky",
        current_wind_speed="5",
        current_wind_dir="NW",
        current_visibility="10000",
        current_sunrise="6:30 AM",
        current_sunset="7:45 PM",
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
