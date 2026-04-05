# tests/test_weather.py
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
