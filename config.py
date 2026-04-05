import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_BASE = Path(__file__).parent

try:
    with open(_BASE / "config.json") as f:
        _cfg = json.load(f)
except FileNotFoundError:
    raise RuntimeError(
        "config.json not found. Copy config.example.json to config.json and fill in your settings."
    )


class Settings:
    def __init__(self) -> None:
        self.location_name: str = _cfg["location_name"]
        self.latitude: str = _cfg["latitude"]
        self.longitude: str = _cfg["longitude"]
        self.calendar_ids: list = _cfg["calendar_ids"]
        self.calendar_max_events: int = _cfg["calendar_max_events"]
        self.data_refresh_minutes: int = _cfg["data_refresh_minutes"]

        # Optional at startup — weather fetch will fail gracefully if absent
        self.owm_api_key: str = os.environ.get("OPEN_WEATHER_MAP_API_KEY", "")

        self.credentials_path: str = str(_BASE / "credentials.json")
        self.token_path: str = str(_BASE / "token.json")
        self.fonts_dir: Path = _BASE / "fonts"


settings = Settings()
