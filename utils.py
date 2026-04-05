from datetime import timezone, datetime


def local_time(utc_dt: datetime) -> datetime:
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(tz=None)


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
