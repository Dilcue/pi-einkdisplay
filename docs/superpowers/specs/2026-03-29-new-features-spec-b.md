# Spec B — New Pages: Stocks, News, Spotify

**Date:** 2026-03-29
**Depends on:** Spec A (transitions + dual-plane render interface)

---

## Overview

Three new body pages following the existing `Page.render(black_draw, red_draw, data)` interface. Each has a corresponding data module in `data/`, a config section, and a web UI settings page.

---

## Shared Conventions

- All pages follow the existing header + 380px body architecture
- Section label: Nokia FC22, 9px, red, 3px letter-spacing, uppercase, top-left of body
- Page indicator dots: bottom-right, same as existing pages — dot count expands as pages are added
- Data fetched in the main refresh cycle alongside weather/calendar; cached between refreshes
- Each new page can be enabled/disabled via config and the web UI display page

---

## 1. Stocks Page

### Layout

```
STOCKS                                    ← section label, red

AAPL    $214.10   +1.4%   ∿∿∿∿∿∿∿∿∿     ← ticker row
TSLA    $172.30   -2.1%   ∿∿∿∿∿∿∿∿∿
SPY     $538.80   +0.6%   ∿∿∿∿∿∿∿∿∿
NVDA    $875.40   +3.2%   ∿∿∿∿∿∿∿∿∿
AMZN    $196.50   -0.8%   ∿∿∿∿∿∿∿∿∿
```

**Ticker row** (Nokia FC22):
- Symbol: 14px black, width 90px
- Price: 13px black, width 100px
- Change: 11px — **red** if positive (`+1.4%`), **black** if negative (`-2.1%`), width 70px
- Sparkline: SVG polyline filling remaining width, height 22px — red stroke if day change positive, black if negative. Intraday data points (up to last 20 periods).

**Max tickers:** 5 (matches body height). Configurable list via web UI.

### Data (`data/stocks.py`)

Uses `yfinance` library (no API key required):

```python
@dataclass
class TickerData:
    symbol: str
    price: str        # "$214.10"
    change: str       # "+1.4%" or "-2.1%"
    positive: bool
    sparkline: list[float]  # normalized 0..1, up to 20 points

def fetch(symbols: list[str]) -> list[TickerData]
```

`yfinance.Ticker(symbol).history(period="1d", interval="5m")` provides intraday points for the sparkline. Sparkline points are normalised to 0–1 within the day's range.

**Market hours awareness:** Outside US market hours (weekends, after 4pm ET) prices are stale — fetch still runs but data is clearly last-close. No special UI treatment needed; price is still valid.

### Config

```json
"stocks_symbols": ["AAPL", "TSLA", "SPY", "NVDA", "AMZN"],
"stocks_enabled": true
```

### Web UI (`/stocks`)

- Text input list of ticker symbols (comma-separated or one per line)
- Enable/disable toggle
- Validate: symbols trimmed and uppercased before save

---

## 2. News Page

### Layout

```
NEWS                                      ← section label, red

1   Fed holds rates steady amid           ← number red, headline black 13px
    inflation uncertainty
    Reuters · 2h ago                      ← source small, grey

2   SpaceX launches 23 more Starlink
    satellites into orbit
    The Verge · 3h ago

3   Apple unveils new iPad Pro with M4
    9to5Mac · 4h ago
```

**Per headline:**
- Number: Nokia FC22 16px red, fixed width 20px
- Headline: Nokia FC22 13px black, wraps to 2 lines max
- Source + age: Nokia FC22 8px grey (`#888`)
- Row spacing: equal thirds of body height (≈126px each)

**Max headlines:** 3.

### Data (`data/news.py`)

Uses `feedparser` library to read any RSS/Atom feed:

```python
@dataclass
class NewsItem:
    title: str
    source: str   # feed title or configured display name
    age: str      # "2h ago", "Just now", etc.

def fetch(feed_url: str, display_name: str) -> list[NewsItem]
```

Title truncated to 80 characters. Age computed from `entry.published_parsed`.

**Default feed:** BBC News Top Stories (`http://feeds.bbci.co.uk/news/rss.xml`). Any RSS/Atom URL works.

### Config

```json
"news_feed_url": "http://feeds.bbci.co.uk/news/rss.xml",
"news_feed_name": "BBC News",
"news_enabled": true
```

### Web UI (`/news`)

- Feed URL text input
- Display name text input (shown as source label on display)
- Enable/disable toggle
- "Test feed" button — hits the URL and shows first 3 titles inline, confirming it works before save

---

## 3. Spotify Page

### Layout

```
NOW PLAYING                               ← section label, red

┌────────┐  Bohemian Rhapsody            ← track 15px black
│        │  Queen                        ← artist 10px grey
│   ♪    │  A Night at the Opera        ← album 9px grey
│        │
└────────┘  ████░░░░░░░░░░░░░░          ← progress bar, red fill
            2:14                5:55     ← times, 8px grey
```

- Art block: 106×106px black square, CD-IconsPC `H` glyph (sun) at 66px grey as placeholder
- Art block left-aligned, info block fills remaining width
- Entire art+info block vertically centered in the space below "NOW PLAYING"
- Progress bar: full width of info column, 5px tall, red fill, grey background

**Idle state** (nothing playing): Art block shows `J` glyph (moon), track = "Nothing playing", artist and album empty, progress bar hidden.

### Data (`data/spotify.py`)

Uses the Spotify Web API with OAuth. Token stored in `data/spotify_token.json` (same pattern as Google Calendar's `token.json`).

```python
@dataclass
class SpotifyData:
    playing: bool
    track: str
    artist: str
    album: str
    progress_ms: int
    duration_ms: int

def fetch(token_path: Path) -> SpotifyData
```

Endpoint: `GET https://api.spotify.com/v1/me/player/currently-playing`

Scopes required: `user-read-currently-playing user-read-playback-state`

Token refresh follows the same pattern as Google Calendar — refresh_token stored in `spotify_token.json`, auto-refreshed when expired.

### Config

```json
"spotify_enabled": true
```

No additional config needed — credentials stored in `data/spotify_credentials.json` (same pattern as `credentials.json` for Google).

### Web UI (`/spotify`)

OAuth flow mirroring the calendar page:
- OAuth status box: connected email / "Not connected"
- Authorize / Re-authorize button → `/spotify/oauth/start`
- Callback at `/spotify/oauth/callback`
- Enable/disable toggle
- Note: requires a Spotify Developer app (free) with `http://<pi-ip>/spotify/oauth/callback` as redirect URI

---

## Files Created / Modified

| File | Change |
|---|---|
| `pages/stocks.py` | New page |
| `pages/news.py` | New page |
| `pages/spotify.py` | New page |
| `data/stocks.py` | New data module |
| `data/news.py` | New data module |
| `data/spotify.py` | New data module |
| `main.py` | Register new pages, fetch new data sources |
| `config.json` / `config.example.json` | New fields for all three pages |
| `web/app.py` | `/stocks`, `/news`, `/spotify`, `/spotify/oauth/*` routes |
| `web/templates/stocks.html` | New |
| `web/templates/news.html` | New |
| `web/templates/spotify.html` | New |
| `web/templates/base.html` | Nav links for new pages |

### Dependencies to add (`requirements.txt`)

- `yfinance` — stocks
- `feedparser` — news
- `spotipy` or raw `requests` for Spotify (prefer raw requests, no extra dependency)

---

## Notes

- New pages slot into the existing page rotation. Order and enable/disable controlled via the display config page in the web UI.
- Spotify page refresh should happen every 30s when the Spotify page is active (track progress changes fast) vs the standard data refresh cycle for others. `main.py` can check `isinstance(current_page, SpotifyPage)` to use a shorter poll interval.
- `yfinance` may be slow on first call per symbol (~1s). Fetch all symbols in parallel using `ThreadPoolExecutor`.
- News feed fetched on the standard `data_refresh_minutes` schedule — no need for faster refresh.
