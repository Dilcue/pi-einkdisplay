import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date

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
    base = "https://api.openweathermap.org/data/2.5"
    params = f"lat={settings.latitude}&lon={settings.longitude}&appid={settings.owm_api_key}&units=imperial"

    current_resp = requests.get(f"{base}/weather?{params}", timeout=10)
    current_resp.raise_for_status()
    current = current_resp.json()

    forecast_resp = requests.get(f"{base}/forecast?{params}", timeout=10)
    forecast_resp.raise_for_status()
    forecast = forecast_resp.json()

    sunset_ts = current["sys"]["sunset"]
    is_day = int(time.time()) <= sunset_ts

    current_icon_code = current["weather"][0]["icon"]

    # Group 3-hour forecast periods by local date
    days: dict[date, list] = defaultdict(list)
    for entry in forecast["list"]:
        local_dt = local_time(datetime.utcfromtimestamp(entry["dt"]))
        days[local_dt.date()].append(entry)

    sorted_days = sorted(days.keys())

    def _day(d: date, force_day: bool = True) -> DayForecast:
        periods = days[d]
        high = max(p["main"]["temp_max"] for p in periods)
        low = min(p["main"]["temp_min"] for p in periods)
        # Use the midday period for condition/icon, fall back to first
        midday = next((p for p in periods if 11 <= local_time(datetime.utcfromtimestamp(p["dt"])).hour <= 14), periods[0])
        icon_code = midday["weather"][0]["icon"]
        return DayForecast(
            day=d.strftime("%a"),
            temp=f"{'%.0f' % high}/{'%.0f' % low}",
            cond=midday["weather"][0]["main"].capitalize(),
            icon=resolve_weather_icon(icon_code, force_day),
        )

    today_date = local_time(datetime.utcnow()).date()
    future_days = [d for d in sorted_days if d >= today_date]

    return WeatherReport(
        last_update=datetime.now().strftime("%I:%M"),
        current_temp=f"{'%.0f' % current['main']['temp']}",
        current_cond=current["weather"][0]["main"].capitalize(),
        current_desc=current["weather"][0]["description"],
        current_wind_speed=f"{'%.0f' % current['wind']['speed']}",
        current_wind_dir=wind_deg_to_dir(current["wind"]["deg"]),
        current_uv_index="N/A",
        current_visibility=str(current.get("visibility", "N/A")),
        current_sunrise=local_time(datetime.utcfromtimestamp(current["sys"]["sunrise"])).strftime("%I:%M %p"),
        current_sunset=local_time(datetime.utcfromtimestamp(sunset_ts)).strftime("%I:%M %p"),
        current_feels_like=f"{'%.0f' % current['main']['feels_like']}",
        current_icon=resolve_weather_icon(current_icon_code, is_day),
        today=_day(future_days[0], force_day=is_day) if len(future_days) > 0 else DayForecast("---", "--/--", "---", ""),
        tomorrow=_day(future_days[1], force_day=True) if len(future_days) > 1 else DayForecast("---", "--/--", "---", ""),
        day3=_day(future_days[2], force_day=True) if len(future_days) > 2 else DayForecast("---", "--/--", "---", ""),
    )
