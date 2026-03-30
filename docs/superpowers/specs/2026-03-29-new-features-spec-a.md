# Spec A — Core System: Transitions + Notifications + Weather Rewrite

**Date:** 2026-03-29
**Depends on:** 800×480 tricolor display redesign spec

---

## Overview

Three system-level changes that must ship before Spec B (new pages):
1. Horizontal wave page transitions
2. NWS weather rewrite with OWM legacy support
3. Persistent notification banner system

---

## 1. Page Transitions

### Behaviour

A horizontal wave sweeps right across the 800px body region when cycling pages:
- **Phase 1 (sweep):** Red stripe leads right, black fill follows behind it. Old content erased.
- **Phase 2 (reveal):** Red stripe leads right again, new content revealed behind it.
- Header (top 100px) is excluded — carried unchanged through every frame.
- Total frames: `2 × N` (default `N=6`). Each frame is a full dual-plane write.

### Per-frame bitplane state (3 zones, advancing left→right)

| Zone | Black plane | Red plane |
|---|---|---|
| Left of stripe (revealed/erased) | New content (phase 2) / white (phase 1) | New content (phase 2) / off (phase 1) |
| Stripe | Off | On (solid red) |
| Right of stripe | Old content | Old content |

### Implementation

**`display.py`** — new function:
```python
def transition(
    old_black: Image, old_red: Image,
    new_black: Image, new_red: Image,
    steps: int = 6
) -> None
```
- Generates `2 × steps` intermediate frame pairs
- Stripe width = `800 // steps`
- Calls `_write(black, red)` for each frame
- `main.py` calls this instead of direct `_write()` when cycling pages
- `page_delay_seconds` timer starts after transition completes

**`config.json`** — add optional `transition_steps: int` (default 6, range 4–10).

---

## 2. Weather Provider Rewrite

### Architecture

`data/weather.py` is split into a provider pattern:

```
data/
  weather.py          # fetch() dispatcher + shared dataclasses
  weather_nws.py      # NWS implementation
  weather_owm.py      # OWM implementation (existing logic, refactored)
```

`fetch()` reads `settings.weather_provider` (`"nws"` | `"owm"`, default `"owm"`) and delegates.

### WeatherReport changes

```python
@dataclass
class WeatherAlert:
    headline: str        # e.g. "Winter Storm Warning"
    expires: datetime

@dataclass
class WeatherReport:
    # ... all existing fields unchanged ...
    alerts: list[WeatherAlert]  # empty list for OWM
```

### NWS implementation (`weather_nws.py`)

Four requests per refresh (results cached in memory between refresh cycles):

1. `GET https://api.weather.gov/points/{lat},{lon}` → gridpoint URLs + nearest station ID (cache permanently — never changes for a given lat/lon)
2. `GET /stations/{stationId}/observations/latest` → current temp, feels_like, wind, conditions
3. `GET /gridpoints/{office}/{x},{y}/forecast` → 7-day daily forecast
4. `GET /alerts/active?point={lat},{lon}` → active alerts list

No API key required. User-Agent header required by NWS: `User-Agent: pi-einkdisplay/1.0`.

### OWM implementation (`weather_owm.py`)

Existing `weather.py` logic moved here verbatim. `alerts` always returns `[]`.

### Config changes

```json
"weather_provider": "owm"
```

---

## 3. Notification System

### `data/notifications.py`

New module. Called by `main.py` after each data refresh.

```python
@dataclass
class Notification:
    id: str              # stable hash of source + event id
    title: str           # event name or alert headline
    subtitle: str        # "2:00 PM today" or alert expires time
    minutes_until: int   # negative = past due (show "NOW")
    source: str          # "calendar" | "weather"
    expires_at: datetime # when to auto-remove (event start + 1hr, or alert expires)

def get_active(app_data: AppData) -> list[Notification]
```

**Calendar:** For each upcoming event, read `event["reminders"]`. If `useDefault`, use the calendar's default (fetched once via `calendarList.get()`). For each reminder with `method == "popup"`, compute trigger = `event_start - minutes`. Fire when `now >= trigger` and `event_start > now - 3600` (auto-expire 1hr after event starts).

**Weather (NWS only):** Each `WeatherAlert` in `WeatherReport.alerts` becomes a `Notification` with `source="weather"`, title = `alert.headline`, expires = `alert.expires`.

### State file

`data/notifications_dismissed.json` — list of dismissed notification IDs. Checked before surfacing any notification. Persists across restarts.

### `main.py` integration

```python
active_notifications = notifications.get_active(app_data)
# pass to render cycle
```

### Banner rendering (`display.py`)

```python
def render_banner(black_draw: ImageDraw, red_draw: ImageDraw, n: Notification) -> None
```

Renders at y=100 (immediately below header divider), height=48px. The banner **overlays** the top 48px of the body — it does not push body content down. Body pages render normally into the full 380px body region; `render_banner()` is called after the body page render and paints over the top strip. No transition when banner appears/disappears — next full frame write includes/excludes it.

**Layout (800×48px strip):**
- Background: black (both planes off on red, all on black)
- Left block (120px wide): red fill on red plane. Large minute count (`15`, or `NOW` if ≤ 0) at Nokia FC22 32px white, `MIN` label at 12px below — drawn on black plane as white (i.e. not drawn = white on e-ink).
- Right area: title at Nokia FC22 22px white, subtitle at 12px grey — drawn on black plane only.

### Web UI

**`/` (index):** New "Notifications" card, hidden when no active notifications. Each row: title, subtitle, Dismiss button.

**`POST /notifications/dismiss`** — appends notification ID to `notifications_dismissed.json`, redirects back to index.

**`web/templates/weather.html`** — expanded API card:
- Provider radio: `NWS (recommended)` / `OpenWeatherMap`
- OWM key field: shown only when OWM selected (JS toggle)
- NWS selected: inline note "Weather alerts supported"
- OWM selected: inline note "Weather alerts not available"
- Refresh interval: unchanged, applies to both

---

## Files Modified

| File | Change |
|---|---|
| `display.py` | Add `transition()`, `render_banner()` |
| `main.py` | Call `transition()` on page cycle, call `notifications.get_active()`, pass to render |
| `data/weather.py` | Dispatcher + shared dataclasses, add `WeatherAlert`, `alerts` field |
| `data/weather_nws.py` | New — NWS implementation |
| `data/weather_owm.py` | New — OWM implementation (moved from weather.py) |
| `data/notifications.py` | New module |
| `data/notifications_dismissed.json` | New state file (gitignored) |
| `config.json` / `config.example.json` | Add `weather_provider`, `transition_steps` |
| `web/app.py` | Add `/notifications/dismiss`, weather provider config handling |
| `web/templates/index.html` | Active notifications card |
| `web/templates/weather.html` | Provider toggle, conditional OWM key, alerts note |

---

## Notes

- NWS points lookup result should be cached to a local file (`data/nws_points_cache.json`) so a restart doesn't require a re-lookup.
- OWM remains the default (`weather_provider: "owm"`) so existing installs are unaffected.
- `transition_steps` × 2 × ~300ms per partial refresh = total transition time. At 6 steps ≈ 3.6s. Expose in config so user can tune for their hardware.
