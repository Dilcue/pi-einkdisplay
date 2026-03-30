# Core System: Transitions + Notifications + Weather Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add horizontal wave page transitions, rewrite weather data fetching to support NWS (with OWM legacy), and implement a persistent notification banner system.

**Architecture:** `display.py` gains a `transition()` function that writes N×2 intermediate dual-plane frames for the wave effect. Weather fetching is split into `weather_nws.py` and `weather_owm.py` behind a common interface. `data/notifications.py` reads calendar reminders and NWS alerts to produce `Notification` objects that `main.py` renders as a persistent banner via `display.render_banner()`.

**Tech Stack:** Python 3, Pillow, requests, pytest. No new pip dependencies.

**Prerequisite:** The 800×480 tricolor display redesign must be implemented first (`docs/superpowers/specs/2026-03-29-800x480-display-redesign.md`). This plan assumes:
- `display.new_image()` → `tuple[Image, ImageDraw, Image, ImageDraw]` (black + red layers)
- `display._write(black: Image, red: Image)` writes both planes to framebuffer
- `Page.render(black_draw, red_draw, data)` dual-draw signature
- `display._WIDTH = 800`, `display._HEIGHT = 480`, `display._HEADER_H = 100`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `display.py` | Modify | Add `transition()`, `render_banner()` |
| `data/weather.py` | Rewrite | Dispatcher + shared dataclasses |
| `data/weather_owm.py` | Create | OWM implementation (moved from old weather.py) |
| `data/weather_nws.py` | Create | NWS implementation |
| `data/nws_points_cache.json` | Create (runtime) | Cached NWS gridpoint lookup |
| `data/notifications.py` | Create | Active notification logic |
| `data/notifications_dismissed.json` | Create (runtime) | Dismissed notification IDs |
| `config.py` | Modify | Add `weather_provider`, `transition_steps` |
| `config.json` / `config.example.json` | Modify | New fields |
| `pages/base.py` | Modify | Add `notifications` field to `AppData` |
| `main.py` | Modify | Transition on page cycle, fetch notifications, render banner |
| `web/app.py` | Modify | `/notifications/dismiss`, weather provider config |
| `web/templates/index.html` | Modify | Active notifications card |
| `web/templates/weather.html` | Modify | Provider toggle |
| `tests/test_transitions.py` | Create | Transition frame pixel tests |
| `tests/test_weather_nws.py` | Create | NWS fetch + parsing tests |
| `tests/test_notifications.py` | Create | Notification trigger logic tests |
| `.gitignore` | Modify | Add `data/notifications_dismissed.json`, `data/nws_points_cache.json` |

---

## Task 1: Test infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create tests package**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Create conftest with shared fixtures**

```python
# tests/conftest.py
import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def black_image():
    img = Image.new("1", (800, 480), 1)
    return img, ImageDraw.Draw(img)


@pytest.fixture
def red_image():
    img = Image.new("1", (800, 480), 0)
    return img, ImageDraw.Draw(img)
```

- [ ] **Step 3: Verify pytest runs**

```bash
cd /path/to/pi-einkdisplay
pip install pytest
pytest tests/ -v
```

Expected: `no tests ran` with exit 0.

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: add test infrastructure"
```

---

## Task 2: Transition function

**Files:**
- Modify: `display.py`
- Create: `tests/test_transitions.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_transitions.py
import pytest
from PIL import Image, ImageDraw
from unittest.mock import patch, call


def make_image(color: int) -> Image.Image:
    """Create a solid 800×480 1-bit image. 0=black, 1=white."""
    return Image.new("1", (800, 480), color)


def test_transition_calls_write_correct_number_of_times():
    """transition() with steps=4 should call _write exactly 8 times."""
    old_black = make_image(1)
    old_red = make_image(0)
    new_black = make_image(1)
    new_red = make_image(0)

    with patch("display._write") as mock_write:
        import display
        display.transition(old_black, old_red, new_black, new_red, steps=4)

    assert mock_write.call_count == 8


def test_transition_header_preserved_from_new():
    """Header region (y < 100) of each frame should match the new page, not old."""
    old_black = make_image(0)   # all black
    new_black = make_image(1)   # all white
    old_red = make_image(0)
    new_red = make_image(0)

    written_frames = []
    with patch("display._write", side_effect=lambda b, r: written_frames.append(b.copy())):
        import display
        display.transition(old_black, old_red, new_black, new_red, steps=4)

    # Every frame header row should be white (from new_black)
    for frame in written_frames:
        pixel = frame.getpixel((400, 50))  # middle of header
        assert pixel == 1, "Header should come from new page (white)"


def test_transition_phase1_stripe_is_red():
    """In phase 1, the leading stripe column should be set on the red plane."""
    old_black = make_image(1)
    new_black = make_image(1)
    old_red = make_image(0)
    new_red = make_image(0)

    red_frames = []
    with patch("display._write", side_effect=lambda b, r: red_frames.append(r.copy())):
        import display
        display.transition(old_black, old_red, new_black, new_red, steps=4)

    # Frame 0 (first phase-1 frame): stripe starts at x=0, width=200
    stripe_pixel = red_frames[0].getpixel((100, 200))   # inside stripe, body region
    assert stripe_pixel == 1, "Red stripe should be active in body during phase 1"


def test_transition_final_frame_matches_new_page():
    """Last frame written should equal new_black / new_red in the body region."""
    old_black = make_image(0)
    new_black = make_image(1)
    old_red = make_image(0)
    new_red = make_image(0)

    written_black = []
    with patch("display._write", side_effect=lambda b, r: written_black.append(b.copy())):
        import display
        display.transition(old_black, old_red, new_black, new_red, steps=4)

    last = written_black[-1]
    # Body region should be white (from new_black)
    pixel = last.getpixel((400, 300))
    assert pixel == 1
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_transitions.py -v
```

Expected: `ImportError` or `AttributeError: module 'display' has no attribute 'transition'`

- [ ] **Step 3: Implement `transition()` in display.py**

Add after the existing `update()` function:

```python
def transition(
    old_black: Image.Image,
    old_red: Image.Image,
    new_black: Image.Image,
    new_red: Image.Image,
    steps: int = 6,
) -> None:
    """Horizontal wave transition: red leads, black follows, body region only."""
    stripe_w = _WIDTH // steps

    for phase in range(2):
        for step in range(steps):
            stripe_x = step * stripe_w
            stripe_end = min(stripe_x + stripe_w, _WIDTH)

            # Start each frame from white/empty
            frame_black = Image.new("1", _SIZE, 1)
            frame_red = Image.new("1", _SIZE, 0)

            # Header: always from new page
            frame_black.paste(new_black.crop((0, 0, _WIDTH, _HEADER_H)), (0, 0))
            frame_red.paste(new_red.crop((0, 0, _WIDTH, _HEADER_H)), (0, 0))

            bd = ImageDraw.Draw(frame_black)
            rd = ImageDraw.Draw(frame_red)

            if phase == 0:
                # Left of stripe: black fill on both planes
                if stripe_x > 0:
                    bd.rectangle([(0, _HEADER_H), (stripe_x - 1, _HEIGHT - 1)], fill=0)
                # Red stripe
                rd.rectangle([(stripe_x, _HEADER_H), (stripe_end - 1, _HEIGHT - 1)], fill=1)
                # Right of old content
                if stripe_end < _WIDTH:
                    region = (stripe_end, _HEADER_H, _WIDTH, _HEIGHT)
                    frame_black.paste(old_black.crop(region), (stripe_end, _HEADER_H))
                    frame_red.paste(old_red.crop(region), (stripe_end, _HEADER_H))
            else:
                # Left of stripe: new content revealed
                if stripe_x > 0:
                    region = (0, _HEADER_H, stripe_x, _HEIGHT)
                    frame_black.paste(new_black.crop(region), (0, _HEADER_H))
                    frame_red.paste(new_red.crop(region), (0, _HEADER_H))
                # Red stripe
                rd.rectangle([(stripe_x, _HEADER_H), (stripe_end - 1, _HEIGHT - 1)], fill=1)
                # Right of stripe: black fill
                if stripe_end < _WIDTH:
                    bd.rectangle([(stripe_end, _HEADER_H), (_WIDTH - 1, _HEIGHT - 1)], fill=0)

            _write(frame_black, frame_red)
```

Also add the constant near the top of `display.py`:

```python
_HEADER_H = 100
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_transitions.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add display.py tests/test_transitions.py
git commit -m "feat: add horizontal wave page transition"
```

---

## Task 3: Wire transition into main.py

**Files:**
- Modify: `main.py`
- Modify: `config.py`, `config.json`, `config.example.json`

- [ ] **Step 1: Add `transition_steps` to config**

In `config.example.json` and `config.json` add:
```json
"transition_steps": 6
```

In `config.py` inside `Settings.__init__`:
```python
self.transition_steps: int = _cfg.get("transition_steps", 6)
```

- [ ] **Step 2: Update main loop to use transition**

Replace the render+update block in `main.py`:

```python
    # Before loop, render initial page without transition
    black_img, black_draw, red_img, red_draw = display.new_image()
    page = pages[page_index]
    page.render(black_draw, red_draw, app_data)
    display._write(black_img, red_img)
    prev_black, prev_red = black_img, red_img

    while True:
        now = time.time()
        if now - last_refresh >= refresh_interval:
            _refresh_weather(app_data)
            _refresh_calendar(app_data)
            last_refresh = now

        buttons.wait_or_advance(settings.page_delay_seconds + page.time_bonus)
        page_index = (page_index + 1) % len(pages)

        if page_index % 2 == 0:
            _log.info("Clearing display before page %d", page_index)
            display.clear()
            time.sleep(0.5)

        black_img, black_draw, red_img, red_draw = display.new_image()
        page = pages[page_index]
        page.render(black_draw, red_draw, app_data)

        display.transition(prev_black, prev_red, black_img, red_img,
                           steps=settings.transition_steps)
        prev_black, prev_red = black_img, red_img
```

- [ ] **Step 3: Commit**

```bash
git add main.py config.py config.json config.example.json
git commit -m "feat: wire transition into main page cycle"
```

---

## Task 4: Weather provider split

**Files:**
- Create: `data/weather_owm.py`
- Create: `data/weather_nws.py`
- Rewrite: `data/weather.py`
- Modify: `config.py`, `config.json`, `config.example.json`

- [ ] **Step 1: Move OWM logic to `data/weather_owm.py`**

`data/weather_owm.py` is the current `data/weather.py` contents with the function renamed to `fetch()` and `alerts: list = []` added to the returned `WeatherReport`. No other changes.

```python
# data/weather_owm.py
# (full contents of current data/weather.py, function kept as fetch())
# Only change: WeatherReport(..., alerts=[]) in the return statement
```

Copy the current `data/weather.py` to `data/weather_owm.py`, then add `alerts=[]` to the `WeatherReport(...)` constructor call at the bottom of `fetch()`.

- [ ] **Step 2: Add `WeatherAlert` + `alerts` field to shared dataclasses**

Rewrite `data/weather.py` as the dispatcher:

```python
# data/weather.py
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date, timezone

import requests

from config import settings
from utils import local_time, wind_deg_to_dir, resolve_weather_icon


@dataclass
class WeatherAlert:
    headline: str      # e.g. "Winter Storm Warning"
    expires: datetime


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
    current_visibility: str
    current_sunrise: str
    current_sunset: str
    current_feels_like: str
    current_icon: str
    today: DayForecast
    tomorrow: DayForecast
    day3: DayForecast
    alerts: list[WeatherAlert] = field(default_factory=list)


def fetch() -> WeatherReport:
    provider = getattr(settings, "weather_provider", "owm")
    if provider == "nws":
        from data import weather_nws
        return weather_nws.fetch()
    from data import weather_owm
    return weather_owm.fetch()
```

- [ ] **Step 3: Add `weather_provider` to config**

`config.example.json` and `config.json`:
```json
"weather_provider": "owm"
```

`config.py` inside `Settings.__init__`:
```python
self.weather_provider: str = _cfg.get("weather_provider", "owm")
```

- [ ] **Step 4: Commit**

```bash
git add data/weather.py data/weather_owm.py config.py config.json config.example.json
git commit -m "refactor: split weather into owm/nws provider modules"
```

---

## Task 5: NWS implementation

**Files:**
- Create: `data/weather_nws.py`
- Create: `tests/test_weather_nws.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_weather_nws.py
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from data.weather import WeatherReport, WeatherAlert


POINTS_RESPONSE = {
    "properties": {
        "gridId": "BOS",
        "gridX": 64,
        "gridY": 51,
        "forecastHourly": "https://api.weather.gov/gridpoints/BOS/64,51/forecast/hourly",
        "forecast": "https://api.weather.gov/gridpoints/BOS/64,51/forecast",
        "observationStations": "https://api.weather.gov/gridpoints/BOS/64,51/stations",
    }
}

STATIONS_RESPONSE = {
    "features": [{"properties": {"stationIdentifier": "KBOS"}}]
}

OBSERVATION_RESPONSE = {
    "properties": {
        "temperature": {"value": 5.0, "unitCode": "wmoUnit:degC"},
        "windSpeed": {"value": 20.0},
        "windDirection": {"value": 270},
        "textDescription": "Partly Cloudy",
        "icon": "https://api.weather.gov/icons/land/day/few?size=medium",
    }
}

FORECAST_RESPONSE = {
    "properties": {
        "periods": [
            {"name": "Today", "isDaytime": True, "temperature": 48,
             "temperatureUnit": "F", "shortForecast": "Partly Cloudy",
             "icon": "https://api.weather.gov/icons/land/day/few?size=medium",
             "startTime": "2026-03-29T08:00:00-05:00"},
            {"name": "Tonight", "isDaytime": False, "temperature": 36,
             "temperatureUnit": "F", "shortForecast": "Clear",
             "icon": "https://api.weather.gov/icons/land/night/skc?size=medium",
             "startTime": "2026-03-29T18:00:00-05:00"},
            {"name": "Monday", "isDaytime": True, "temperature": 52,
             "temperatureUnit": "F", "shortForecast": "Rain",
             "icon": "https://api.weather.gov/icons/land/day/rain?size=medium",
             "startTime": "2026-03-30T08:00:00-05:00"},
            {"name": "Monday Night", "isDaytime": False, "temperature": 41,
             "temperatureUnit": "F", "shortForecast": "Rain",
             "icon": "https://api.weather.gov/icons/land/night/rain?size=medium",
             "startTime": "2026-03-30T18:00:00-05:00"},
            {"name": "Tuesday", "isDaytime": True, "temperature": 61,
             "temperatureUnit": "F", "shortForecast": "Sunny",
             "icon": "https://api.weather.gov/icons/land/day/skc?size=medium",
             "startTime": "2026-03-31T08:00:00-05:00"},
            {"name": "Tuesday Night", "isDaytime": False, "temperature": 44,
             "temperatureUnit": "F", "shortForecast": "Clear",
             "icon": "https://api.weather.gov/icons/land/night/skc?size=medium",
             "startTime": "2026-03-31T18:00:00-05:00"},
        ]
    }
}

ALERTS_RESPONSE = {
    "features": [
        {
            "properties": {
                "headline": "Winter Storm Warning",
                "expires": "2026-03-30T06:00:00-05:00",
                "severity": "Severe",
                "event": "Winter Storm Warning",
            }
        }
    ]
}

ALERTS_EMPTY = {"features": []}


def _mock_get(url, **kwargs):
    m = MagicMock()
    m.raise_for_status = MagicMock()
    if "points/" in url and "stations" not in url and "forecast" not in url:
        m.json.return_value = POINTS_RESPONSE
    elif "stations" in url and "observations" not in url:
        m.json.return_value = STATIONS_RESPONSE
    elif "observations/latest" in url:
        m.json.return_value = OBSERVATION_RESPONSE
    elif "forecast" in url:
        m.json.return_value = FORECAST_RESPONSE
    elif "alerts/active" in url:
        m.json.return_value = ALERTS_RESPONSE
    return m


def test_fetch_returns_weather_report(tmp_path, monkeypatch):
    monkeypatch.setattr("data.weather_nws._CACHE_PATH", tmp_path / "cache.json")
    monkeypatch.setattr("config.settings.latitude", "42.36")
    monkeypatch.setattr("config.settings.longitude", "-71.06")

    with patch("requests.get", side_effect=_mock_get):
        from data import weather_nws
        result = weather_nws.fetch()

    assert isinstance(result, WeatherReport)
    assert result.current_temp == "41"   # 5°C → 41°F
    assert result.today.temp == "48/36"


def test_fetch_returns_alerts(tmp_path, monkeypatch):
    monkeypatch.setattr("data.weather_nws._CACHE_PATH", tmp_path / "cache.json")
    monkeypatch.setattr("config.settings.latitude", "42.36")
    monkeypatch.setattr("config.settings.longitude", "-71.06")

    with patch("requests.get", side_effect=_mock_get):
        from data import weather_nws
        result = weather_nws.fetch()

    assert len(result.alerts) == 1
    assert result.alerts[0].headline == "Winter Storm Warning"


def test_fetch_empty_alerts(tmp_path, monkeypatch):
    monkeypatch.setattr("data.weather_nws._CACHE_PATH", tmp_path / "cache.json")
    monkeypatch.setattr("config.settings.latitude", "42.36")
    monkeypatch.setattr("config.settings.longitude", "-71.06")

    def mock_get_no_alerts(url, **kwargs):
        m = _mock_get(url, **kwargs)
        if "alerts/active" in url:
            m.json.return_value = ALERTS_EMPTY
        return m

    with patch("requests.get", side_effect=mock_get_no_alerts):
        from data import weather_nws
        result = weather_nws.fetch()

    assert result.alerts == []


def test_points_cache_is_reused(tmp_path, monkeypatch):
    monkeypatch.setattr("data.weather_nws._CACHE_PATH", tmp_path / "cache.json")
    monkeypatch.setattr("config.settings.latitude", "42.36")
    monkeypatch.setattr("config.settings.longitude", "-71.06")

    call_count = {"n": 0}
    def counting_get(url, **kwargs):
        if "points/" in url and "stations" not in url and "forecast" not in url:
            call_count["n"] += 1
        return _mock_get(url, **kwargs)

    with patch("requests.get", side_effect=counting_get):
        from data import weather_nws
        weather_nws.fetch()
        weather_nws.fetch()

    assert call_count["n"] == 1, "Points endpoint should only be called once (cached)"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_weather_nws.py -v
```

Expected: `ModuleNotFoundError: No module named 'data.weather_nws'`

- [ ] **Step 3: Implement `data/weather_nws.py`**

```python
# data/weather_nws.py
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import settings
from data.weather import WeatherAlert, WeatherReport, DayForecast
from utils import resolve_weather_icon, wind_deg_to_dir, local_time

_CACHE_PATH = Path(__file__).parent / "nws_points_cache.json"


def _solar_time(lat: float, lon: float, rising: bool) -> str:
    """Approximate sunrise/sunset via the NOAA simplified algorithm."""
    import math
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    lon_hour = lon / 15
    t = day_of_year + ((6 if rising else 18) - lon_hour) / 24
    M = (0.9856 * t) - 3.289
    L = M + 1.916 * math.sin(math.radians(M)) + 0.020 * math.sin(math.radians(2 * M)) + 282.634
    L = L % 360
    RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L)))) % 360
    Lquad = (math.floor(L / 90)) * 90
    RAquad = (math.floor(RA / 90)) * 90
    RA = (RA + Lquad - RAquad) / 15
    sinDec = 0.39782 * math.sin(math.radians(L))
    cosDec = math.cos(math.asin(sinDec))
    cosH = (math.cos(math.radians(90.833)) - sinDec * math.sin(math.radians(lat))) / (cosDec * math.cos(math.radians(lat)))
    if cosH > 1 or cosH < -1:
        return "N/A"
    H = (360 - math.degrees(math.acos(cosH))) / 15 if rising else math.degrees(math.acos(cosH)) / 15
    T = H + RA - 0.06571 * t - 6.622
    UT = (T - lon_hour) % 24
    local_h = int(UT) % 24
    local_m = int((UT % 1) * 60)
    suffix = "AM" if local_h < 12 else "PM"
    disp_h = local_h if local_h <= 12 else local_h - 12
    disp_h = 12 if disp_h == 0 else disp_h
    return f"{disp_h:02d}:{local_m:02d} {suffix}"


def _compute_sunrise(lat: float, lon: float) -> str:
    return _solar_time(lat, lon, rising=True)


def _compute_sunset(lat: float, lon: float) -> str:
    return _solar_time(lat, lon, rising=False)
_UA = {"User-Agent": "pi-einkdisplay/1.0 (github.com/pi-einkdisplay)"}
_BASE = "https://api.weather.gov"

# In-memory cache for the current process lifetime
_points_cache: dict | None = None


def _c_to_f(c: float) -> str:
    return str(round(c * 9 / 5 + 32))


def _ms_to_mph(ms: float) -> str:
    return str(round(ms * 2.237))


def _load_points() -> dict:
    """Return cached gridpoint data, fetching and saving if not cached."""
    global _points_cache
    if _points_cache is not None:
        return _points_cache

    if _CACHE_PATH.exists():
        cached = json.loads(_CACHE_PATH.read_text())
        lat, lon = cached.get("lat"), cached.get("lon")
        if lat == settings.latitude and lon == settings.longitude:
            _points_cache = cached
            return _points_cache

    r = requests.get(
        f"{_BASE}/points/{settings.latitude},{settings.longitude}", headers=_UA, timeout=10
    )
    r.raise_for_status()
    props = r.json()["properties"]

    stations_r = requests.get(props["observationStations"], headers=_UA, timeout=10)
    stations_r.raise_for_status()
    station_id = stations_r.json()["features"][0]["properties"]["stationIdentifier"]

    _points_cache = {
        "lat": settings.latitude,
        "lon": settings.longitude,
        "grid_id": props["gridId"],
        "grid_x": props["gridX"],
        "grid_y": props["gridY"],
        "forecast_url": props["forecast"],
        "station_id": station_id,
    }
    _CACHE_PATH.write_text(json.dumps(_points_cache))
    return _points_cache


def _icon_from_nws_url(url: str, is_day: bool) -> str:
    """Map NWS icon URL to CD-IconsPC glyph via resolve_weather_icon."""
    url = url.lower()
    if "skc" in url or "few" in url:
        code = "01d" if is_day else "01n"
    elif "sct" in url or "bkn" in url:
        code = "02d" if is_day else "02n"
    elif "ovc" in url or "fg" in url:
        code = "04d"
    elif "rain" in url or "ra" in url:
        code = "10d"
    elif "tsra" in url or "hi_tsra" in url:
        code = "11d"
    elif "snow" in url or "sn" in url:
        code = "13d"
    else:
        code = "04d"
    return resolve_weather_icon(code, is_day)


def fetch() -> WeatherReport:
    pts = _load_points()

    obs_r = requests.get(
        f"{_BASE}/stations/{pts['station_id']}/observations/latest",
        headers=_UA, timeout=10
    )
    obs_r.raise_for_status()
    obs = obs_r.json()["properties"]

    temp_c = obs["temperature"]["value"] or 0.0
    wind_ms = obs["windSpeed"]["value"] or 0.0
    wind_deg = obs["windDirection"]["value"] or 0
    desc = obs.get("textDescription", "")

    now_ts = int(time.time())
    is_day = 6 <= datetime.now().hour <= 20  # approximate

    forecast_r = requests.get(pts["forecast_url"], headers=_UA, timeout=10)
    forecast_r.raise_for_status()
    periods = forecast_r.json()["properties"]["periods"]

    # Build day forecasts from daytime periods
    day_periods = [p for p in periods if p["isDaytime"]]
    night_periods = [p for p in periods if not p["isDaytime"]]

    def _day(day_p: dict, night_p: dict | None) -> DayForecast:
        high = day_p["temperature"]
        low = night_p["temperature"] if night_p else high - 10
        return DayForecast(
            day=day_p["name"],
            temp=f"{high}/{low}",
            cond=day_p["shortForecast"],
            icon=_icon_from_nws_url(day_p["icon"], True),
        )

    today = _day(day_periods[0], night_periods[0] if night_periods else None)
    tomorrow = _day(day_periods[1], night_periods[1] if len(night_periods) > 1 else None) if len(day_periods) > 1 else today
    day3 = _day(day_periods[2], night_periods[2] if len(night_periods) > 2 else None) if len(day_periods) > 2 else today

    alerts_r = requests.get(
        f"{_BASE}/alerts/active",
        params={"point": f"{settings.latitude},{settings.longitude}"},
        headers=_UA, timeout=10
    )
    alerts_r.raise_for_status()
    alerts = []
    for feature in alerts_r.json().get("features", []):
        p = feature["properties"]
        try:
            expires = datetime.fromisoformat(p["expires"])
        except (KeyError, ValueError):
            continue
        alerts.append(WeatherAlert(headline=p.get("headline", p.get("event", "")), expires=expires))

    return WeatherReport(
        last_update=datetime.now().strftime("%I:%M"),
        current_temp=_c_to_f(temp_c),
        current_cond=desc,
        current_desc=desc,
        current_wind_speed=_ms_to_mph(wind_ms),
        current_wind_dir=wind_deg_to_dir(int(wind_deg)),
        current_visibility="N/A",
        current_sunrise=_compute_sunrise(float(settings.latitude), float(settings.longitude)),
        current_sunset=_compute_sunset(float(settings.latitude), float(settings.longitude)),
        current_feels_like=_c_to_f(temp_c),  # NWS obs doesn't include feels_like; use temp as fallback
        current_icon=_icon_from_nws_url(obs.get("icon", ""), is_day),
        today=today,
        tomorrow=tomorrow,
        day3=day3,
        alerts=alerts,
    )
```

- [ ] **Step 4: Add cache files to .gitignore**

```
data/nws_points_cache.json
data/notifications_dismissed.json
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/test_weather_nws.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add data/weather_nws.py data/weather.py tests/test_weather_nws.py .gitignore
git commit -m "feat: add NWS weather provider with alerts support"
```

---

## Task 6: Notification system

**Files:**
- Create: `data/notifications.py`
- Modify: `pages/base.py`
- Create: `tests/test_notifications.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_notifications.py
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from data.notifications import Notification, get_active
from data.weather import WeatherAlert, WeatherReport, DayForecast
from pages.base import AppData


def _make_weather(alerts=None) -> WeatherReport:
    dummy_day = DayForecast("Mon", "50/40", "Clear", "H")
    return WeatherReport(
        last_update="10:00", current_temp="50", current_cond="Clear",
        current_desc="Clear", current_wind_speed="5", current_wind_dir="N",
        current_visibility="10", current_sunrise="06:30 AM", current_sunset="07:30 PM",
        current_feels_like="48", current_icon="H",
        today=dummy_day, tomorrow=dummy_day, day3=dummy_day,
        alerts=alerts or [],
    )


def _make_event(minutes_until: int, title: str = "Test Event") -> dict:
    """Build a minimal Google Calendar event dict."""
    start = datetime.now(tz=timezone.utc) + timedelta(minutes=minutes_until)
    return {
        "id": f"event_{title}",
        "summary": title,
        "start": {"dateTime": start.isoformat()},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 15}]},
    }


def test_calendar_event_triggers_at_correct_time(tmp_path, monkeypatch):
    monkeypatch.setattr("data.notifications._DISMISSED_PATH", tmp_path / "dismissed.json")
    event = _make_event(minutes_until=10)  # 10 min away, reminder fires at 15 min
    data = AppData(weather=_make_weather(), calendar_events=[event])

    result = get_active(data)

    assert len(result) == 1
    assert result[0].title == "Test Event"
    assert result[0].source == "calendar"


def test_calendar_event_not_triggered_too_early(tmp_path, monkeypatch):
    monkeypatch.setattr("data.notifications._DISMISSED_PATH", tmp_path / "dismissed.json")
    event = _make_event(minutes_until=60)  # 60 min away, reminder at 15 min — not yet
    data = AppData(weather=_make_weather(), calendar_events=[event])

    result = get_active(data)

    assert len(result) == 0


def test_weather_alert_surfaces(tmp_path, monkeypatch):
    monkeypatch.setattr("data.notifications._DISMISSED_PATH", tmp_path / "dismissed.json")
    alert = WeatherAlert(
        headline="Winter Storm Warning",
        expires=datetime.now(tz=timezone.utc) + timedelta(hours=6),
    )
    data = AppData(weather=_make_weather(alerts=[alert]), calendar_events=[])

    result = get_active(data)

    assert len(result) == 1
    assert result[0].source == "weather"
    assert result[0].title == "Winter Storm Warning"


def test_dismissed_notification_is_excluded(tmp_path, monkeypatch):
    monkeypatch.setattr("data.notifications._DISMISSED_PATH", tmp_path / "dismissed.json")
    event = _make_event(minutes_until=10)
    data = AppData(weather=_make_weather(), calendar_events=[event])

    # Dismiss it
    from data.notifications import dismiss
    notifs = get_active(data)
    dismiss(notifs[0].id)

    result = get_active(data)
    assert len(result) == 0


def test_expired_event_not_surfaced(tmp_path, monkeypatch):
    monkeypatch.setattr("data.notifications._DISMISSED_PATH", tmp_path / "dismissed.json")
    event = _make_event(minutes_until=-90)  # 90 min in the past
    data = AppData(weather=_make_weather(), calendar_events=[event])

    result = get_active(data)

    assert len(result) == 0
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_notifications.py -v
```

Expected: `ImportError: cannot import name 'Notification' from 'data.notifications'`

- [ ] **Step 3: Implement `data/notifications.py`**

```python
# data/notifications.py
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pages.base import AppData

_DISMISSED_PATH = Path(__file__).parent / "notifications_dismissed.json"


@dataclass
class Notification:
    id: str
    title: str
    subtitle: str
    minutes_until: int
    source: str        # "calendar" | "weather"
    expires_at: datetime


def _load_dismissed() -> set[str]:
    if not _DISMISSED_PATH.exists():
        return set()
    return set(json.loads(_DISMISSED_PATH.read_text()))


def dismiss(notification_id: str) -> None:
    dismissed = _load_dismissed()
    dismissed.add(notification_id)
    _DISMISSED_PATH.write_text(json.dumps(list(dismissed)))


def _make_id(*parts: str) -> str:
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:12]


def get_active(data: AppData) -> list[Notification]:
    now = datetime.now(tz=timezone.utc)
    dismissed = _load_dismissed()
    results: list[Notification] = []

    # Calendar notifications
    for event in (data.calendar_events or []):
        start_str = (event.get("start") or {}).get("dateTime")
        if not start_str:
            continue
        try:
            start = datetime.fromisoformat(start_str)
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        # Auto-expire 1 hour after event starts
        expires_at = start + timedelta(hours=1)
        if now > expires_at:
            continue

        reminders = event.get("reminders", {})
        overrides = reminders.get("overrides", [])
        if reminders.get("useDefault", True):
            # Default: 30 minutes
            overrides = [{"method": "popup", "minutes": 30}]

        for reminder in overrides:
            if reminder.get("method") != "popup":
                continue
            trigger = start - timedelta(minutes=reminder["minutes"])
            if now < trigger:
                continue

            nid = _make_id("calendar", event.get("id", ""), str(reminder["minutes"]))
            if nid in dismissed:
                continue

            minutes_until = int((start - now).total_seconds() / 60)
            time_str = start.astimezone().strftime("%I:%M %p").lstrip("0")
            subtitle = f"{time_str} today" if minutes_until >= 0 else "now"

            results.append(Notification(
                id=nid,
                title=event.get("summary", "Event"),
                subtitle=subtitle,
                minutes_until=minutes_until,
                source="calendar",
                expires_at=expires_at,
            ))

    # Weather alert notifications
    if data.weather:
        for alert in (data.weather.alerts or []):
            if now > alert.expires:
                continue
            nid = _make_id("weather", alert.headline)
            if nid in dismissed:
                continue
            results.append(Notification(
                id=nid,
                title=alert.headline,
                subtitle=f"Until {alert.expires.astimezone().strftime('%I:%M %p')}",
                minutes_until=0,
                source="weather",
                expires_at=alert.expires,
            ))

    return results
```

- [ ] **Step 4: Add `notifications` to `AppData` in `pages/base.py`**

```python
# pages/base.py — add import and field
from data.notifications import Notification   # add this import

@dataclass
class AppData:
    weather: WeatherReport | None = None
    calendar_events: list[CalendarEvent] | None = None
    notifications: list[Notification] = field(default_factory=list)
```

Also add `from dataclasses import dataclass, field` if `field` is not already imported.

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/test_notifications.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add data/notifications.py pages/base.py tests/test_notifications.py
git commit -m "feat: add notification system for calendar reminders and weather alerts"
```

---

## Task 7: Notification banner rendering

**Files:**
- Modify: `display.py`
- Modify: `main.py`

- [ ] **Step 1: Implement `render_banner()` in display.py**

Add after `transition()`:

```python
def render_banner(
    black_draw: ImageDraw.ImageDraw,
    red_draw: ImageDraw.ImageDraw,
    notification: "Notification",
) -> None:
    """Draw persistent notification banner at y=100, overlaying body top."""
    from pathlib import Path
    from PIL import ImageFont
    fonts_dir = Path(__file__).parent / "fonts"
    font_lg = ImageFont.truetype(str(fonts_dir / "nokiafc22.ttf"), 32)
    font_sm = ImageFont.truetype(str(fonts_dir / "nokiafc22.ttf"), 12)
    font_md = ImageFont.truetype(str(fonts_dir / "nokiafc22.ttf"), 22)

    BANNER_Y = _HEADER_H        # 100
    BANNER_H = 48
    RED_BLOCK_W = 120

    # Black background strip (black_draw: fill 0 = black)
    black_draw.rectangle(
        [(0, BANNER_Y), (_WIDTH - 1, BANNER_Y + BANNER_H - 1)], fill=0
    )

    # Red block on left (red_draw: fill 1 = red)
    red_draw.rectangle(
        [(0, BANNER_Y), (RED_BLOCK_W - 1, BANNER_Y + BANNER_H - 1)], fill=1
    )

    # Countdown text in red block — white on black_draw (fill 1 = white on e-ink)
    mins = notification.minutes_until
    count_str = "NOW" if mins <= 0 else str(abs(mins))
    label_str = "" if mins <= 0 else "MIN"
    # Center count_str horizontally in the red block
    black_draw.text((10, BANNER_Y + 4), count_str, font=font_lg, fill=1)
    if label_str:
        black_draw.text((10, BANNER_Y + 34), label_str, font=font_sm, fill=1)

    # Title and subtitle to the right of the red block
    title = notification.title[:40]  # truncate if needed
    black_draw.text((RED_BLOCK_W + 12, BANNER_Y + 6), title, font=font_md, fill=1)
    black_draw.text((RED_BLOCK_W + 12, BANNER_Y + 32), notification.subtitle, font=font_sm, fill=1)
```

- [ ] **Step 2: Wire banner into main.py render cycle**

In `main.py`, add the import and update the render block:

```python
from data import notifications as notif_module

# In the while loop, after page.render():
active = notif_module.get_active(app_data)
if active:
    display.render_banner(black_draw, red_draw, active[0])
```

- [ ] **Step 3: Commit**

```bash
git add display.py main.py
git commit -m "feat: render notification banner on display"
```

---

## Task 8: Web UI — notification dismiss + weather provider

**Files:**
- Modify: `web/app.py`
- Modify: `web/templates/index.html`
- Modify: `web/templates/weather.html`

- [ ] **Step 1: Add dismiss endpoint to web/app.py**

```python
# web/app.py — add import
from data.notifications import dismiss as dismiss_notification, get_active as get_active_notifications
from pages.base import AppData as _AppData

# Add route
@app.route("/notifications/dismiss", methods=["POST"])
def notifications_dismiss():
    nid = request.form.get("id", "")
    if nid:
        dismiss_notification(nid)
    return redirect(url_for("index"))
```

Update the `index()` route to pass active notifications:

```python
@app.route("/")
def index():
    cfg = _load_config()
    status = _service_status()
    uptime = _service_uptime()
    oauth_email = _oauth_connected_email()

    # Load active notifications for display
    try:
        from pages.base import AppData
        from data.calendar_client import fetch as cal_fetch
        from data import weather as wx
        ad = AppData()
        try:
            ad.weather = wx.fetch()
        except Exception:
            pass
        active_notifs = get_active_notifications(ad)
    except Exception:
        active_notifs = []

    return render_template("index.html",
        cfg=cfg, status=status, uptime=uptime,
        oauth_connected=oauth_email is not None,
        oauth_email=oauth_email,
        active_notifications=active_notifs,
    )
```

- [ ] **Step 2: Add notifications card to index.html**

Add before the closing `{% endblock %}`:

```html
{% if active_notifications %}
<div class="card">
  <h2>Active Notifications</h2>
  {% for n in active_notifications %}
  <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #eee;">
    <div>
      <strong>{{ n.title }}</strong>
      <span style="font-size:12px;color:#666;margin-left:8px;">{{ n.subtitle }}</span>
    </div>
    <form method="post" action="/notifications/dismiss" style="margin:0">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <input type="hidden" name="id" value="{{ n.id }}">
      <button type="submit" class="btn btn-secondary" style="padding:4px 10px;font-size:12px;">Dismiss</button>
    </form>
  </div>
  {% endfor %}
</div>
{% endif %}
```

- [ ] **Step 3: Update weather.html for provider toggle**

Replace the existing `<div class="card"><h2>API</h2>` card:

```html
<div class="card">
  <h2>Provider</h2>
  <div class="form-group">
    <label>Weather provider</label>
    <div style="display:flex;flex-direction:column;gap:8px;margin-top:4px;">
      <label style="display:flex;align-items:center;gap:8px;font-weight:normal;">
        <input type="radio" name="weather_provider" value="nws"
          {% if cfg.weather_provider == 'nws' %}checked{% endif %}
          onchange="toggleProvider(this.value)">
        NWS (recommended) — free, no key, US only
        <span id="nws-note" style="font-size:12px;color:#2a7a2a;{% if cfg.weather_provider != 'nws' %}display:none{% endif %}">
          ✓ Weather alerts supported
        </span>
      </label>
      <label style="display:flex;align-items:center;gap:8px;font-weight:normal;">
        <input type="radio" name="weather_provider" value="owm"
          {% if cfg.weather_provider != 'nws' %}checked{% endif %}
          onchange="toggleProvider(this.value)">
        OpenWeatherMap
        <span id="owm-note" style="font-size:12px;color:#888;{% if cfg.weather_provider == 'nws' %}display:none{% endif %}">
          Weather alerts not available
        </span>
      </label>
    </div>
  </div>
  <div id="owm-key-section" style="{% if cfg.weather_provider == 'nws' %}display:none{% endif %}">
    <div class="form-group">
      <label for="owm_api_key">OpenWeatherMap API key</label>
      <input type="password" id="owm_api_key" name="owm_api_key" value=""
        placeholder="{{ '••••••••' if has_api_key else 'Enter API key' }}"
        autocomplete="new-password">
      {% if has_api_key %}<p style="font-size:12px;color:#666;margin-top:4px;">Key is set. Enter a new value to replace it.</p>{% endif %}
    </div>
  </div>
  <div class="form-group">
    <label for="data_refresh_minutes">Refresh interval</label>
    <select name="data_refresh_minutes" id="data_refresh_minutes" style="max-width:150px;">
      {% for m in [15, 30, 60, 120] %}
        <option value="{{ m }}" {% if m == cfg.data_refresh_minutes %}selected{% endif %}>{{ m }} minutes</option>
      {% endfor %}
    </select>
  </div>
</div>

<script>
function toggleProvider(val) {
  document.getElementById('owm-key-section').style.display = val === 'owm' ? '' : 'none';
  document.getElementById('nws-note').style.display = val === 'nws' ? '' : 'none';
  document.getElementById('owm-note').style.display = val === 'owm' ? '' : 'none';
}
</script>
```

- [ ] **Step 4: Update weather route in web/app.py to save `weather_provider`**

In the weather POST handler, add:
```python
cfg["weather_provider"] = request.form.get("weather_provider", "owm")
```

And in the GET handler, ensure the template receives `cfg.weather_provider` (it will via the existing `cfg` dict).

- [ ] **Step 5: Commit**

```bash
git add web/app.py web/templates/index.html web/templates/weather.html
git commit -m "feat: add notification dismiss UI and weather provider toggle"
```

---

## Task 9: Final integration test

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 2: Verify config.example.json is complete**

Confirm `config.example.json` contains:
```json
{
  "weather_provider": "owm",
  "transition_steps": 6
}
```

- [ ] **Step 3: Final commit**

```bash
git add -u
git commit -m "feat: Spec A complete — transitions, NWS weather, notifications"
```
