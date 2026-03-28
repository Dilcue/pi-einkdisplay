import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_BASE = Path(__file__).parent

with open(_BASE / "config.json") as f:
    _cfg = json.load(f)


class Settings:
    location_name: str = _cfg["location_name"]
    latitude: str = _cfg["latitude"]
    longitude: str = _cfg["longitude"]
    calendar_display_name: str = _cfg["calendar_display_name"]
    page_delay_seconds: int = _cfg["page_delay_seconds"]
    data_refresh_minutes: int = _cfg["data_refresh_minutes"]

    owm_api_key: str = os.environ["OPEN_WEATHER_MAP_API_KEY"]

    credentials_path: str = str(_BASE / "credentials.json")
    token_path: str = str(_BASE / "token.json")

    fonts_dir: Path = _BASE / "fonts"


settings = Settings()
