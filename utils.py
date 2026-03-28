from datetime import timezone, datetime


def local_time(utc_dt: datetime) -> datetime:
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


def wind_deg_to_dir(wind_deg: float) -> str:
    val = int((wind_deg / 22.5) + 0.5)
    arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return arr[val % 16]


def resolve_weather_icon(code: str, is_day: bool) -> str:
    if code.startswith("01"):
        return "H" if is_day else "J"
    elif code.startswith("02") or code.startswith("04"):
        return "E" if is_day else "D"
    elif code.startswith("03"):
        return "D"
    elif code.startswith("09") or code.startswith("10"):
        return "B"
    elif code.startswith("11"):
        return "F"
    elif code.startswith("13"):
        return "C"
    elif code.startswith("50"):
        return "G"
    return ""
