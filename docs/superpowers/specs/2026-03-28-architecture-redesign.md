# Pi E-Ink Display — Architecture Redesign Spec

**Date:** 2026-03-28
**Status:** Approved

---

## Overview

Refactor the existing single-file weather e-ink display script into a clean, modular Python package. The goals are: fix broken functionality (Google token refresh), establish a maintainable structure for adding new data sources and pages, and adopt conventional config/secrets management.

---

## Project Structure

```
pi-einkdisplay/
├── main.py                      # Loop, page rotation, data refresh scheduling
├── config.py                    # Loads .env + config.json, exposes settings
├── utils.py                     # localTime, windDegToDir, resolveWeatherIcon
├── display.py                   # Papirus wrapper (init, clear, update)
├── config.json                  # App preferences — committed
├── config.example.json          # Template with placeholder values — committed
├── .env                         # Secrets — gitignored, lives on Pi only
├── .env.example                 # Template with placeholder keys — committed
├── deploy.sh                    # rsync deploy script (see Backlog)
├── data/
│   ├── weather.py               # OWM fetch + WeatherReport dataclass
│   └── calendar_client.py       # Google Calendar fetch + token refresh
├── pages/
│   ├── base.py                  # Abstract Page class
│   ├── clock.py
│   ├── weather_current.py
│   ├── weather_forecast.py
│   └── calendar_page.py
└── fonts/
    ├── nokiafc22.ttf
    └── CD-IconsPC.ttf
```

---

## Config & Secrets

**`.env`** — secrets, always gitignored:
```
OPEN_WEATHER_MAP_API_KEY=your_key_here
```
Loaded at startup via `python-dotenv`. New API keys for future data sources get a new line here.

**`config.json`** — app preferences, safe to commit:
```json
{
    "location_name": "Your City, ST",
    "latitude": "YOUR_LATITUDE",
    "longitude": "YOUR_LONGITUDE",
    "calendar_display_name": "Family Calendar",
    "page_delay_seconds": 7,
    "data_refresh_minutes": 60
}
```

`config.py` loads both and exposes a single settings object. Nothing else in the app reads env vars or opens config files directly.

---

## Data Layer

### `data/weather.py`
- Fetches from OpenWeatherMap `onecall` API
- Returns a `WeatherReport` dataclass (typed fields, replaces string-attribute class)
- Raises on failed fetch so `main.py` can decide to show stale data or skip

### `data/calendar_client.py`
- Full OAuth2 lifecycle: loads `token.json`, auto-refreshes expired tokens, browser flow only on first run
- Returns a list of `CalendarEvent` dataclasses
- `credentials.json` and `token.json` paths are configurable so they can live outside the project directory

Both fetchers are plain functions. `main.py` calls them on a timer and stores results in a shared `AppData` object passed to pages.

```python
class AppData:
    weather: WeatherReport | None
    calendar_events: list[CalendarEvent] | None
```

If a fetch fails, the app logs the error and retains the last good data rather than crashing.

---

## Page Base Class & Render Contract

```python
# pages/base.py
from abc import ABC, abstractmethod

class Page(ABC):
    time_bonus = 0  # extra seconds this page holds (override in subclass)

    @abstractmethod
    def render(self, draw, data: AppData):
        """Draw this page. draw = ImageDraw instance, data = AppData"""
        pass
```

Pages registered in `main.py`:
```python
pages = [
    ClockPage(),
    WeatherCurrentPage(),
    WeatherForecastPage(),
    CalendarPage(),
]
```

Adding a page = create file in `pages/`, add one line to the list.
Removing a page = comment it out.

---

## Main Loop

```
1. Load config + secrets
2. Init display
3. Register pages
4. Loop:
   a. Refresh data if stale (timestamp-based, no threading)
   b. Clear display
   c. Render current page
   d. Sleep (PAGE_DELAY + page.time_bonus)
   e. Advance page index
```

No threads. Simple timestamp check for data staleness. Pi Zero W (512MB RAM) does not warrant threading complexity at this stage.

---

## Backlog

### Deployment Formalization
The deploy workflow (rsync from Mac → Pi, systemd service for boot/restart) needs to be formalized into a proper process. Revisit when the project stabilizes post-refactor.
- `deploy.sh` stub will be created but process is not finalized
- `systemd` service setup to be documented in a future spec

### Gemini Home Automation Integration
Google Gemini home automation as a future data source / interactive page. Unrefined — revisit when the platform matures and requirements are clearer.

---

## Out of Scope (This Spec)

- Web UI for configuration
- Any interactive button functionality beyond what currently exists
- Additional data sources beyond weather and calendar
