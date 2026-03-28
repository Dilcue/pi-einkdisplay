import time
from dataclasses import dataclass
from datetime import datetime

import requests

from config import settings
from utils import local_time, wind_deg_to_dir, resolve_weather_icon


@dataclass
class DayForecast:
    day: str
    temp: str
    cond: str
    icon: str


@dataclass
class WeatherReport:
    last_update: str
    current_temp: str
    current_cond: str
    current_desc: str
    current_wind_speed: str
    current_wind_dir: str
    current_uv_index: str
    current_visibility: str
    current_sunrise: str
    current_sunset: str
    current_feels_like: str
    current_icon: str
    today: DayForecast
    tomorrow: DayForecast
    day3: DayForecast


def fetch() -> WeatherReport:
    url = (
        "https://api.openweathermap.org/data/2.5/onecall"
        f"?lat={settings.latitude}"
        f"&lon={settings.longitude}"
        "&exclude=minutely,hourly,alerts"
        f"&appid={settings.owm_api_key}"
        "&units=imperial"
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    body = response.json()

    current = body["current"]
    daily = body["daily"]

    sunset_ts = current["sunset"]
    is_day = int(time.time()) <= sunset_ts

    def _day(d, force_day=True) -> DayForecast:
        icon_code = d["weather"][0]["icon"]
        return DayForecast(
            day=local_time(datetime.utcfromtimestamp(d["dt"])).strftime("%a"),
            temp=f"{'%.0f' % d['temp']['max']}/{'%.0f' % d['temp']['min']}",
            cond=d["weather"][0]["main"].capitalize(),
            icon=resolve_weather_icon(icon_code, force_day),
        )

    current_icon_code = current["weather"][0]["icon"]

    return WeatherReport(
        last_update=datetime.now().strftime("%I:%M"),
        current_temp=f"{'%.0f' % current['temp']}",
        current_cond=current["weather"][0]["main"].capitalize(),
        current_desc=current["weather"][0]["description"],
        current_wind_speed=f"{'%.0f' % current['wind_speed']}",
        current_wind_dir=wind_deg_to_dir(current["wind_deg"]),
        current_uv_index=str(current["uvi"]),
        current_visibility=str(current["visibility"]),
        current_sunrise=local_time(datetime.utcfromtimestamp(current["sunrise"])).strftime("%I:%M %p"),
        current_sunset=local_time(datetime.utcfromtimestamp(sunset_ts)).strftime("%I:%M %p"),
        current_feels_like=f"{'%.0f' % current['feels_like']}",
        current_icon=resolve_weather_icon(current_icon_code, is_day),
        today=_day(daily[0], force_day=is_day),
        tomorrow=_day(daily[1], force_day=True),
        day3=_day(daily[2], force_day=True),
    )
