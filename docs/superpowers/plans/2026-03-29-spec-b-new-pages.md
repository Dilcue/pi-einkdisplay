# New Pages: Stocks, News, Spotify — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three new body pages — Stocks (ticker list with sparklines), News (3 headlines from RSS), and Spotify (now playing) — each with a data module, page renderer, and web UI config page.

**Architecture:** Each feature is a self-contained `data/<name>.py` + `pages/<name>_page.py` pair registered in `main.py`'s `_PAGE_REGISTRY`. Web UI follows the existing Flask pattern. All three pages use the dual-plane `render(black_draw, red_draw, data)` interface.

**Tech Stack:** Python 3, Pillow, `yfinance`, `feedparser`, `requests` (Spotify). Nokia FC22 + CD-IconsPC fonts.

**Prerequisite:** Spec A implemented. `AppData` has `stocks`, `news`, `spotify` fields added in this plan.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `data/stocks.py` | Create | Fetch ticker prices + sparkline via yfinance |
| `data/news.py` | Create | Fetch RSS headlines via feedparser |
| `data/spotify.py` | Create | Fetch now-playing via Spotify Web API |
| `data/spotify_token.json` | Runtime | OAuth token (gitignored) |
| `data/spotify_credentials.json` | User-provided | Spotify app client_id/secret |
| `pages/stocks_page.py` | Create | Render stocks page |
| `pages/news_page.py` | Create | Render news page |
| `pages/spotify_page.py` | Create | Render Spotify page |
| `pages/base.py` | Modify | Add `stocks`, `news`, `spotify` to `AppData` |
| `main.py` | Modify | Register pages, fetch new data, Spotify fast-poll |
| `config.py` | Modify | New config fields |
| `config.json` / `config.example.json` | Modify | New fields |
| `web/app.py` | Modify | `/stocks`, `/news`, `/spotify`, Spotify OAuth routes |
| `web/templates/stocks.html` | Create | Stocks config UI |
| `web/templates/news.html` | Create | News config UI |
| `web/templates/spotify.html` | Create | Spotify OAuth + config UI |
| `web/templates/base.html` | Modify | Nav links |
| `tests/test_stocks.py` | Create | Stocks data parsing tests |
| `tests/test_news.py` | Create | News fetch + age formatting tests |
| `tests/test_spotify.py` | Create | Spotify data parsing tests |
| `.gitignore` | Modify | Add `data/spotify_token.json` |
| `requirements.txt` | Modify | Add yfinance, feedparser |

---

## Task 1: Dependencies

- [ ] **Step 1: Add to requirements.txt**

```
yfinance
feedparser
```

- [ ] **Step 2: Install**

```bash
pip install yfinance feedparser
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add yfinance and feedparser"
```

---

## Task 2: Stocks data module

**Files:**
- Create: `data/stocks.py`
- Create: `tests/test_stocks.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_stocks.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from data.stocks import TickerData, fetch


def _mock_ticker(symbol: str, close_prices: list[float], current: float) -> MagicMock:
    m = MagicMock()
    df = pd.DataFrame({"Close": close_prices},
                      index=pd.date_range("2026-03-29", periods=len(close_prices), freq="5min"))
    m.history.return_value = df
    m.fast_info = MagicMock()
    m.fast_info.last_price = current
    m.fast_info.previous_close = close_prices[0]
    return m


def test_fetch_returns_ticker_data():
    mock_ticker = _mock_ticker("AAPL", [210.0, 211.0, 212.0, 214.0], current=214.0)
    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = fetch(["AAPL"])
    assert len(result) == 1
    assert result[0].symbol == "AAPL"
    assert result[0].price == "$214.00"


def test_positive_change_is_positive():
    mock_ticker = _mock_ticker("AAPL", [200.0, 205.0, 210.0, 214.0], current=214.0)
    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = fetch(["AAPL"])
    assert result[0].positive is True
    assert result[0].change.startswith("+")


def test_negative_change_is_negative():
    mock_ticker = _mock_ticker("TSLA", [180.0, 175.0, 172.0, 170.0], current=170.0)
    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = fetch(["TSLA"])
    assert result[0].positive is False
    assert result[0].change.startswith("-")


def test_sparkline_normalized_0_to_1():
    mock_ticker = _mock_ticker("SPY", [100.0, 110.0, 120.0, 130.0], current=130.0)
    with patch("yfinance.Ticker", return_value=mock_ticker):
        result = fetch(["SPY"])
    spark = result[0].sparkline
    assert min(spark) >= 0.0
    assert max(spark) <= 1.0


def test_empty_symbols_returns_empty():
    result = fetch([])
    assert result == []
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_stocks.py -v
```

Expected: `ImportError: cannot import name 'TickerData' from 'data.stocks'`

- [ ] **Step 3: Implement `data/stocks.py`**

```python
# data/stocks.py
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import yfinance as yf


@dataclass
class TickerData:
    symbol: str
    price: str          # "$214.10"
    change: str         # "+1.4%" or "-2.1%"
    positive: bool
    sparkline: list[float]  # normalised 0..1, up to 20 points


def _fetch_one(symbol: str) -> TickerData:
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1d", interval="5m")
    closes = hist["Close"].tolist()[-20:] if not hist.empty else []

    current = ticker.fast_info.last_price or 0.0
    prev_close = ticker.fast_info.previous_close or current or 1.0

    pct = ((current - prev_close) / prev_close * 100) if prev_close else 0.0
    positive = pct >= 0
    change_str = f"{'+' if positive else ''}{pct:.1f}%"
    price_str = f"${current:.2f}"

    # Normalise sparkline
    if closes and max(closes) != min(closes):
        lo, hi = min(closes), max(closes)
        spark = [(v - lo) / (hi - lo) for v in closes]
    else:
        spark = [0.5] * len(closes)

    return TickerData(symbol=symbol, price=price_str, change=change_str,
                      positive=positive, sparkline=spark)


def fetch(symbols: list[str]) -> list[TickerData]:
    if not symbols:
        return []
    results: dict[str, TickerData] = {}
    with ThreadPoolExecutor(max_workers=min(len(symbols), 5)) as ex:
        futures = {ex.submit(_fetch_one, s): s for s in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                results[sym] = future.result()
            except Exception:
                pass
    # Return in original order
    return [results[s] for s in symbols if s in results]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_stocks.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add data/stocks.py tests/test_stocks.py
git commit -m "feat: add stocks data module with sparklines"
```

---

## Task 3: Stocks page renderer

**Files:**
- Create: `pages/stocks_page.py`
- Modify: `pages/base.py`

- [ ] **Step 1: Add `stocks` field to AppData**

```python
# pages/base.py
from data.stocks import TickerData  # add import

@dataclass
class AppData:
    weather: WeatherReport | None = None
    calendar_events: list[CalendarEvent] | None = None
    notifications: list[Notification] = field(default_factory=list)
    stocks: list[TickerData] = field(default_factory=list)
```

- [ ] **Step 2: Implement `pages/stocks_page.py`**

```python
# pages/stocks_page.py
from PIL import ImageFont, ImageDraw, Image
from pathlib import Path

from pages.base import AppData, Page

_FONTS_DIR = Path(__file__).parent.parent / "fonts"
_F_SYMBOL = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 28)
_F_PRICE  = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 26)
_F_CHANGE = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 22)
_F_LABEL  = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 18)

_BLACK = 0
_WHITE = 1
_HEADER_H = 100
_BODY_H = 380
_WIDTH = 800
_ROW_H = _BODY_H // 5  # 76px per row


class StocksPage(Page):
    def render(self, black_draw: ImageDraw.ImageDraw, red_draw: ImageDraw.ImageDraw, data: AppData) -> None:
        # Section label
        red_draw.text((24, _HEADER_H + 8), "STOCKS", font=_F_LABEL, fill=_WHITE)

        tickers = (data.stocks or [])[:5]
        label_y = _HEADER_H + 8 + 20  # below section label

        for i, ticker in enumerate(tickers):
            y = label_y + i * _ROW_H + (_ROW_H - 28) // 2

            # Symbol
            black_draw.text((24, y), ticker.symbol, font=_F_SYMBOL, fill=_BLACK)

            # Price
            black_draw.text((140, y), ticker.price, font=_F_PRICE, fill=_BLACK)

            # Change — red if positive, black if negative
            change_draw = red_draw if ticker.positive else black_draw
            change_draw.text((280, y + 2), ticker.change, font=_F_CHANGE, fill=_WHITE if ticker.positive else _BLACK)

            # Sparkline SVG-style via PIL polyline
            if ticker.sparkline:
                spark_x0, spark_x1 = 380, _WIDTH - 24
                spark_y0, spark_y1 = y + 4, y + 28
                spark_w = spark_x1 - spark_x0
                spark_h = spark_y1 - spark_y0
                pts = [
                    (int(spark_x0 + j / (len(ticker.sparkline) - 1) * spark_w),
                     int(spark_y1 - v * spark_h))
                    for j, v in enumerate(ticker.sparkline)
                ]
                draw = red_draw if ticker.positive else black_draw
                fill = _WHITE if ticker.positive else _BLACK
                if len(pts) > 1:
                    draw.line(pts, fill=fill, width=2)

        # Page dots
        self._draw_dots(black_draw, red_draw, active_index=3, total=5)

    def _draw_dots(self, bd, rd, active_index: int, total: int) -> None:
        dot_r = 7
        gap = 18
        x_start = _WIDTH - 24 - (total - 1) * gap
        y = _HEADER_H + _BODY_H - 12
        for i in range(total):
            cx = x_start + i * gap
            if i == active_index:
                rd.ellipse([(cx - dot_r, y - dot_r), (cx + dot_r, y + dot_r)], fill=1)
            else:
                bd.ellipse([(cx - dot_r, y - dot_r), (cx + dot_r, y + dot_r)], outline=0, fill=1)
                bd.ellipse([(cx - dot_r + 2, y - dot_r + 2), (cx + dot_r - 2, y + dot_r - 2)], fill=1)
```

- [ ] **Step 3: Commit**

```bash
git add pages/stocks_page.py pages/base.py
git commit -m "feat: add stocks page renderer"
```

---

## Task 4: News data module

**Files:**
- Create: `data/news.py`
- Create: `tests/test_news.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_news.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import time
from data.news import NewsItem, fetch


def _mock_feed(titles: list[str]) -> MagicMock:
    m = MagicMock()
    m.bozo = False
    m.feed.title = "BBC News"
    entries = []
    for i, title in enumerate(titles):
        e = MagicMock()
        e.title = title
        e.published_parsed = time.gmtime(
            (datetime.now(tz=timezone.utc).timestamp() - (i + 1) * 3600)
        )
        entries.append(e)
    m.entries = entries
    return m


def test_fetch_returns_three_items():
    feed = _mock_feed(["Headline 1", "Headline 2", "Headline 3", "Headline 4"])
    with patch("feedparser.parse", return_value=feed):
        result = fetch("http://example.com/rss", "BBC News")
    assert len(result) == 3


def test_fetch_item_has_correct_title():
    feed = _mock_feed(["Big News Story Today"])
    with patch("feedparser.parse", return_value=feed):
        result = fetch("http://example.com/rss", "BBC")
    assert result[0].title == "Big News Story Today"


def test_fetch_age_formats_hours():
    feed = _mock_feed(["Story"])  # 1 hour ago
    with patch("feedparser.parse", return_value=feed):
        result = fetch("http://example.com/rss", "BBC")
    assert "1h" in result[0].age


def test_fetch_source_uses_display_name():
    feed = _mock_feed(["Story"])
    with patch("feedparser.parse", return_value=feed):
        result = fetch("http://example.com/rss", "My Feed")
    assert result[0].source == "My Feed"


def test_fetch_truncates_long_titles():
    long_title = "A" * 100
    feed = _mock_feed([long_title])
    with patch("feedparser.parse", return_value=feed):
        result = fetch("http://example.com/rss", "Test")
    assert len(result[0].title) <= 80
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_news.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `data/news.py`**

```python
# data/news.py
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser


@dataclass
class NewsItem:
    title: str
    source: str
    age: str    # "2h ago", "Just now"


def _format_age(published_parsed) -> str:
    if not published_parsed:
        return ""
    pub_ts = time.mktime(published_parsed)
    delta = int(time.time() - pub_ts)
    if delta < 60:
        return "Just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


def fetch(feed_url: str, display_name: str) -> list[NewsItem]:
    parsed = feedparser.parse(feed_url)
    items = []
    for entry in parsed.entries[:3]:
        title = (entry.get("title") or "")[:80]
        items.append(NewsItem(
            title=title,
            source=display_name,
            age=_format_age(entry.get("published_parsed")),
        ))
    return items
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_news.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add data/news.py tests/test_news.py
git commit -m "feat: add news RSS data module"
```

---

## Task 5: News page renderer

**Files:**
- Create: `pages/news_page.py`
- Modify: `pages/base.py`

- [ ] **Step 1: Add `news` field to AppData**

```python
# pages/base.py — add import and field
from data.news import NewsItem

@dataclass
class AppData:
    # ... existing fields ...
    news: list[NewsItem] = field(default_factory=list)
```

- [ ] **Step 2: Implement `pages/news_page.py`**

```python
# pages/news_page.py
from PIL import ImageFont, ImageDraw
from pathlib import Path

from pages.base import AppData, Page

_FONTS_DIR = Path(__file__).parent.parent / "fonts"
_F_LABEL   = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 18)
_F_NUM     = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 32)
_F_BODY    = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 26)
_F_SRC     = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 16)

_BLACK = 0
_WHITE = 1
_HEADER_H = 100
_BODY_H = 380
_WIDTH = 800
_ROW_H = _BODY_H // 3  # ~126px per headline


class NewsPage(Page):
    def render(self, black_draw: ImageDraw.ImageDraw, red_draw: ImageDraw.ImageDraw, data: AppData) -> None:
        # Section label
        red_draw.text((24, _HEADER_H + 8), "NEWS", font=_F_LABEL, fill=_WHITE)

        items = (data.news or [])[:3]
        row_start = _HEADER_H + 8 + 22

        for i, item in enumerate(items):
            y = row_start + i * _ROW_H

            # Number in red
            red_draw.text((24, y + 4), str(i + 1), font=_F_NUM, fill=_WHITE)

            # Headline — wrap to 2 lines at ~52 chars per line
            title = item.title
            line1 = title[:52]
            line2 = title[52:104] if len(title) > 52 else ""
            black_draw.text((80, y), line1, font=_F_BODY, fill=_BLACK)
            if line2:
                black_draw.text((80, y + 30), line2, font=_F_BODY, fill=_BLACK)

            # Source + age
            src_text = f"{item.source} · {item.age}"
            src_y = y + 60 if line2 else y + 30
            black_draw.text((80, src_y), src_text, font=_F_SRC, fill=0x44)

        # Page dots
        self._draw_dots(black_draw, red_draw, active_index=4, total=5)

    def _draw_dots(self, bd, rd, active_index: int, total: int) -> None:
        dot_r = 7
        gap = 18
        x_start = _WIDTH - 24 - (total - 1) * gap
        y = _HEADER_H + _BODY_H - 12
        for i in range(total):
            cx = x_start + i * gap
            if i == active_index:
                rd.ellipse([(cx - dot_r, y - dot_r), (cx + dot_r, y + dot_r)], fill=1)
            else:
                bd.ellipse([(cx - dot_r, y - dot_r), (cx + dot_r, y + dot_r)], outline=0, fill=1)
                bd.ellipse([(cx - dot_r + 2, y - dot_r + 2), (cx + dot_r - 2, y + dot_r - 2)], fill=1)
```

- [ ] **Step 3: Commit**

```bash
git add pages/news_page.py pages/base.py
git commit -m "feat: add news page renderer"
```

---

## Task 6: Spotify data module

**Files:**
- Create: `data/spotify.py`
- Create: `tests/test_spotify.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add to .gitignore**

```
data/spotify_token.json
data/spotify_credentials.json
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_spotify.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from data.spotify import SpotifyData, fetch, _refresh_token_if_needed


PLAYING_RESPONSE = {
    "is_playing": True,
    "item": {
        "name": "Bohemian Rhapsody",
        "artists": [{"name": "Queen"}],
        "album": {"name": "A Night at the Opera"},
        "duration_ms": 355000,
    },
    "progress_ms": 134000,
}

TOKEN_DATA = {
    "access_token": "test_access",
    "refresh_token": "test_refresh",
    "expires_at": 9999999999,  # far future
    "token_type": "Bearer",
}


def test_fetch_returns_playing_data(tmp_path):
    token_path = tmp_path / "spotify_token.json"
    token_path.write_text(json.dumps(TOKEN_DATA))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = PLAYING_RESPONSE

    with patch("requests.get", return_value=mock_resp):
        result = fetch(token_path)

    assert result.playing is True
    assert result.track == "Bohemian Rhapsody"
    assert result.artist == "Queen"
    assert result.album == "A Night at the Opera"
    assert result.progress_ms == 134000
    assert result.duration_ms == 355000


def test_fetch_returns_idle_when_204(tmp_path):
    token_path = tmp_path / "spotify_token.json"
    token_path.write_text(json.dumps(TOKEN_DATA))

    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch("requests.get", return_value=mock_resp):
        result = fetch(token_path)

    assert result.playing is False
    assert result.track == ""


def test_fetch_returns_idle_when_no_token(tmp_path):
    token_path = tmp_path / "nonexistent_token.json"
    result = fetch(token_path)
    assert result.playing is False


def test_token_refresh_called_when_expired(tmp_path):
    expired_token = {**TOKEN_DATA, "expires_at": 0}  # already expired
    token_path = tmp_path / "spotify_token.json"
    token_path.write_text(json.dumps(expired_token))
    creds_path = tmp_path / "spotify_credentials.json"
    creds_path.write_text(json.dumps({"client_id": "cid", "client_secret": "csec"}))

    refresh_resp = MagicMock()
    refresh_resp.status_code = 200
    refresh_resp.json.return_value = {
        "access_token": "new_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    play_resp = MagicMock()
    play_resp.status_code = 204

    with patch("requests.post", return_value=refresh_resp), \
         patch("requests.get", return_value=play_resp):
        result = fetch(token_path, creds_path=creds_path)

    new_data = json.loads(token_path.read_text())
    assert new_data["access_token"] == "new_token"
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
pytest tests/test_spotify.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Implement `data/spotify.py`**

```python
# data/spotify.py
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests

_DEFAULT_TOKEN_PATH = Path(__file__).parent / "spotify_token.json"
_DEFAULT_CREDS_PATH = Path(__file__).parent / "spotify_credentials.json"
_API_BASE = "https://api.spotify.com/v1"


@dataclass
class SpotifyData:
    playing: bool
    track: str
    artist: str
    album: str
    progress_ms: int
    duration_ms: int


_IDLE = SpotifyData(playing=False, track="", artist="", album="",
                    progress_ms=0, duration_ms=0)


def _load_token(token_path: Path) -> dict | None:
    if not token_path.exists():
        return None
    return json.loads(token_path.read_text())


def _refresh_token_if_needed(token_path: Path, creds_path: Path) -> str | None:
    token = _load_token(token_path)
    if not token:
        return None

    if time.time() < token.get("expires_at", 0) - 60:
        return token["access_token"]

    if not creds_path.exists():
        return token.get("access_token")  # try anyway

    creds = json.loads(creds_path.read_text())
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        },
        auth=(creds["client_id"], creds["client_secret"]),
        timeout=10,
    )
    if resp.status_code != 200:
        return token.get("access_token")

    new_token = resp.json()
    token["access_token"] = new_token["access_token"]
    token["expires_at"] = int(time.time()) + new_token.get("expires_in", 3600)
    if "refresh_token" in new_token:
        token["refresh_token"] = new_token["refresh_token"]
    token_path.write_text(json.dumps(token))
    return token["access_token"]


def fetch(
    token_path: Path = _DEFAULT_TOKEN_PATH,
    creds_path: Path = _DEFAULT_CREDS_PATH,
) -> SpotifyData:
    access_token = _refresh_token_if_needed(token_path, creds_path)
    if not access_token:
        return _IDLE

    resp = requests.get(
        f"{_API_BASE}/me/player/currently-playing",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code == 204:
        return _IDLE
    if resp.status_code != 200:
        return _IDLE

    data = resp.json()
    item = data.get("item") or {}
    artists = item.get("artists") or [{}]
    return SpotifyData(
        playing=data.get("is_playing", False),
        track=item.get("name", ""),
        artist=artists[0].get("name", "") if artists else "",
        album=(item.get("album") or {}).get("name", ""),
        progress_ms=data.get("progress_ms", 0),
        duration_ms=item.get("duration_ms", 0),
    )
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/test_spotify.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add data/spotify.py tests/test_spotify.py .gitignore
git commit -m "feat: add Spotify now-playing data module"
```

---

## Task 7: Spotify page renderer

**Files:**
- Create: `pages/spotify_page.py`
- Modify: `pages/base.py`

- [ ] **Step 1: Add `spotify` field to AppData**

```python
# pages/base.py
from data.spotify import SpotifyData

@dataclass
class AppData:
    # ... existing fields ...
    spotify: SpotifyData | None = None
```

- [ ] **Step 2: Implement `pages/spotify_page.py`**

```python
# pages/spotify_page.py
from PIL import ImageFont, ImageDraw
from pathlib import Path

from pages.base import AppData, Page

_FONTS_DIR = Path(__file__).parent.parent / "fonts"
_F_LABEL  = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 18)
_F_TRACK  = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 30)
_F_ARTIST = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 20)
_F_ALBUM  = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 18)
_F_TIME   = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 16)
_F_ICON   = ImageFont.truetype(str(_FONTS_DIR / "CD-IconsPC.ttf"), 66)

_BLACK = 0
_WHITE = 1
_HEADER_H = 100
_BODY_H = 380
_WIDTH = 800

_ART_X, _ART_Y = 24, 0   # relative to body
_ART_SIZE = 106
_INFO_X = _ART_X + _ART_SIZE + 20


class SpotifyPage(Page):
    def render(self, black_draw: ImageDraw.ImageDraw, red_draw: ImageDraw.ImageDraw, data: AppData) -> None:
        sp = data.spotify

        # Section label
        red_draw.text((24, _HEADER_H + 8), "NOW PLAYING", font=_F_LABEL, fill=_WHITE)

        label_bottom = _HEADER_H + 8 + 22
        remaining_h = _BODY_H - (label_bottom - _HEADER_H)  # space below label

        # Vertically center the art+info block
        content_h = _ART_SIZE
        center_y = label_bottom + (remaining_h - content_h) // 2

        art_y = center_y
        info_y = art_y

        # Art block (black square)
        black_draw.rectangle(
            [(_ART_X, art_y), (_ART_X + _ART_SIZE - 1, art_y + _ART_SIZE - 1)], fill=_BLACK
        )
        # Glyph inside art block
        glyph = "H" if (sp and sp.playing) else "J"
        black_draw.text((_ART_X + 18, art_y + 16), glyph, font=_F_ICON, fill=_WHITE)

        if sp and sp.playing:
            black_draw.text((_INFO_X, info_y), sp.track[:30], font=_F_TRACK, fill=_BLACK)
            black_draw.text((_INFO_X, info_y + 34), sp.artist[:40], font=_F_ARTIST, fill=_BLACK)
            black_draw.text((_INFO_X, info_y + 56), sp.album[:40], font=_F_ALBUM, fill=0x44)

            # Progress bar
            bar_y = info_y + _ART_SIZE - 20
            bar_w = _WIDTH - _INFO_X - 24
            # Background
            black_draw.rectangle([(_INFO_X, bar_y), (_INFO_X + bar_w - 1, bar_y + 5)], fill=0xAA)
            # Fill
            if sp.duration_ms > 0:
                fill_w = int(bar_w * sp.progress_ms / sp.duration_ms)
                if fill_w > 0:
                    red_draw.rectangle([(_INFO_X, bar_y), (_INFO_X + fill_w - 1, bar_y + 5)], fill=_WHITE)

            # Times
            def _fmt(ms: int) -> str:
                s = ms // 1000
                return f"{s // 60}:{s % 60:02d}"
            black_draw.text((_INFO_X, bar_y + 8), _fmt(sp.progress_ms), font=_F_TIME, fill=_BLACK)
            dur_str = _fmt(sp.duration_ms)
            black_draw.text((_WIDTH - 24 - len(dur_str) * 9, bar_y + 8), dur_str, font=_F_TIME, fill=_BLACK)
        else:
            black_draw.text((_INFO_X, info_y + 30), "Nothing playing", font=_F_ARTIST, fill=0x66)

        self._draw_dots(black_draw, red_draw, active_index=2, total=5)

    def _draw_dots(self, bd, rd, active_index: int, total: int) -> None:
        dot_r = 7
        gap = 18
        x_start = _WIDTH - 24 - (total - 1) * gap
        y = _HEADER_H + _BODY_H - 12
        for i in range(total):
            cx = x_start + i * gap
            if i == active_index:
                rd.ellipse([(cx - dot_r, y - dot_r), (cx + dot_r, y + dot_r)], fill=1)
            else:
                bd.ellipse([(cx - dot_r, y - dot_r), (cx + dot_r, y + dot_r)], outline=0, fill=1)
                bd.ellipse([(cx - dot_r + 2, y - dot_r + 2), (cx + dot_r - 2, y + dot_r - 2)], fill=1)
```

- [ ] **Step 3: Commit**

```bash
git add pages/spotify_page.py pages/base.py
git commit -m "feat: add Spotify now-playing page renderer"
```

---

## Task 8: Wire new pages into main.py

**Files:**
- Modify: `main.py`
- Modify: `config.py`, `config.json`, `config.example.json`

- [ ] **Step 1: Add config fields**

`config.example.json` and `config.json`:
```json
"stocks_symbols": ["AAPL", "TSLA", "SPY"],
"stocks_enabled": false,
"news_feed_url": "http://feeds.bbci.co.uk/news/rss.xml",
"news_feed_name": "BBC News",
"news_enabled": false,
"spotify_enabled": false
```

`config.py` inside `Settings.__init__`:
```python
self.stocks_symbols: list[str] = _cfg.get("stocks_symbols", [])
self.stocks_enabled: bool = _cfg.get("stocks_enabled", False)
self.news_feed_url: str = _cfg.get("news_feed_url", "")
self.news_feed_name: str = _cfg.get("news_feed_name", "News")
self.news_enabled: bool = _cfg.get("news_enabled", False)
self.spotify_enabled: bool = _cfg.get("spotify_enabled", False)
```

- [ ] **Step 2: Register pages and fetch functions in main.py**

```python
# Add imports
from pages.stocks_page import StocksPage
from pages.news_page import NewsPage
from pages.spotify_page import SpotifyPage
from data import stocks as stocks_module
from data import news as news_module
from data import spotify as spotify_module

# Update _PAGE_REGISTRY
_PAGE_REGISTRY = {
    "clock": ClockPage,
    "weather_current": WeatherCurrentPage,
    "weather_forecast": WeatherForecastPage,
    "calendar": CalendarPage,
    "stocks": StocksPage,
    "news": NewsPage,
    "spotify": SpotifyPage,
}

# Add refresh helpers
def _refresh_stocks(app_data: AppData) -> None:
    if not settings.stocks_enabled:
        return
    try:
        app_data.stocks = stocks_module.fetch(settings.stocks_symbols)
        _log.info("Stocks updated (%d tickers)", len(app_data.stocks))
    except Exception as e:
        _log.error("Stocks fetch failed: %s", e)


def _refresh_news(app_data: AppData) -> None:
    if not settings.news_enabled:
        return
    try:
        app_data.news = news_module.fetch(settings.news_feed_url, settings.news_feed_name)
        _log.info("News updated (%d items)", len(app_data.news))
    except Exception as e:
        _log.error("News fetch failed: %s", e)


def _refresh_spotify(app_data: AppData) -> None:
    if not settings.spotify_enabled:
        return
    try:
        app_data.spotify = spotify_module.fetch()
    except Exception as e:
        _log.error("Spotify fetch failed: %s", e)
```

- [ ] **Step 3: Call new refresh functions in main loop**

In `main()`, add to the initial data fetch and the timed refresh block:
```python
_refresh_stocks(app_data)
_refresh_news(app_data)
_refresh_spotify(app_data)
```

For Spotify fast-poll, update the render loop:

```python
        # Spotify needs faster refresh when active
        current_page = pages[page_index]
        if isinstance(current_page, SpotifyPage) and settings.spotify_enabled:
            _refresh_spotify(app_data)
```

- [ ] **Step 4: Commit**

```bash
git add main.py config.py config.json config.example.json
git commit -m "feat: register new pages and data fetchers in main loop"
```

---

## Task 9: Web UI — Stocks + News config pages

**Files:**
- Create: `web/templates/stocks.html`
- Create: `web/templates/news.html`
- Modify: `web/app.py`
- Modify: `web/templates/base.html`

- [ ] **Step 1: Add stocks route to web/app.py**

```python
@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    cfg = _load_config()
    if request.method == "POST":
        raw = request.form.get("stocks_symbols", "")
        symbols = [s.strip().upper() for s in raw.replace(",", "\n").splitlines() if s.strip()]
        cfg["stocks_symbols"] = symbols
        cfg["stocks_enabled"] = "stocks_enabled" in request.form
        _save_config(cfg)
        try:
            _restart_display()
            flash("Stocks settings saved. Display restarting…", "success")
        except RuntimeError:
            flash("Settings saved but display restart failed.", "warning")
        return redirect(url_for("stocks"))
    return render_template("stocks.html", cfg=cfg)
```

- [ ] **Step 2: Create web/templates/stocks.html**

```html
{% extends "base.html" %}
{% block content %}
<h1>Stocks</h1>
<form method="post">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <div class="card">
    <h2>Tickers</h2>
    <div class="form-group">
      <label for="stocks_enabled">
        <input type="checkbox" id="stocks_enabled" name="stocks_enabled"
          {% if cfg.stocks_enabled %}checked{% endif %}>
        Enable stocks page
      </label>
    </div>
    <div class="form-group">
      <label for="stocks_symbols">Ticker symbols (one per line or comma-separated, max 5)</label>
      <textarea id="stocks_symbols" name="stocks_symbols" rows="5" style="font-family:monospace">{{ cfg.stocks_symbols | join('\n') }}</textarea>
    </div>
  </div>
  <button type="submit" class="btn btn-primary">Save &amp; Restart Display</button>
</form>
{% endblock %}
```

- [ ] **Step 3: Add news route to web/app.py**

```python
@app.route("/news", methods=["GET", "POST"])
def news():
    cfg = _load_config()
    test_result = None
    if request.method == "POST":
        if "test_feed" in request.form:
            # Test feed without saving
            import feedparser
            url = request.form.get("news_feed_url", "")
            try:
                parsed = feedparser.parse(url)
                titles = [e.get("title", "(no title)") for e in parsed.entries[:3]]
                test_result = titles if titles else ["No entries found"]
            except Exception as e:
                test_result = [f"Error: {e}"]
        else:
            cfg["news_feed_url"] = request.form.get("news_feed_url", "")
            cfg["news_feed_name"] = request.form.get("news_feed_name", "News")
            cfg["news_enabled"] = "news_enabled" in request.form
            _save_config(cfg)
            try:
                _restart_display()
                flash("News settings saved. Display restarting…", "success")
            except RuntimeError:
                flash("Settings saved but display restart failed.", "warning")
            return redirect(url_for("news"))
    return render_template("news.html", cfg=cfg, test_result=test_result)
```

- [ ] **Step 4: Create web/templates/news.html**

```html
{% extends "base.html" %}
{% block content %}
<h1>News</h1>
<form method="post">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <div class="card">
    <h2>RSS Feed</h2>
    <div class="form-group">
      <label for="news_enabled">
        <input type="checkbox" id="news_enabled" name="news_enabled"
          {% if cfg.news_enabled %}checked{% endif %}>
        Enable news page
      </label>
    </div>
    <div class="form-group">
      <label for="news_feed_url">Feed URL</label>
      <input type="text" id="news_feed_url" name="news_feed_url"
        value="{{ cfg.news_feed_url }}" placeholder="https://feeds.bbci.co.uk/news/rss.xml">
    </div>
    <div class="form-group">
      <label for="news_feed_name">Display name</label>
      <input type="text" id="news_feed_name" name="news_feed_name" value="{{ cfg.news_feed_name }}">
    </div>
    {% if test_result %}
    <div class="card" style="background:#f5f5f5;margin-top:12px;">
      <h3>Feed preview</h3>
      <ul>{% for t in test_result %}<li>{{ t }}</li>{% endfor %}</ul>
    </div>
    {% endif %}
    <button type="submit" name="test_feed" value="1" class="btn btn-secondary">Test Feed</button>
  </div>
  <button type="submit" class="btn btn-primary">Save &amp; Restart Display</button>
</form>
{% endblock %}
```

- [ ] **Step 5: Add nav links to base.html**

In the `<nav>` section, add:
```html
<a href="/stocks" {% if request.path == '/stocks' %}class="active"{% endif %}>Stocks</a>
<a href="/news" {% if request.path == '/news' %}class="active"{% endif %}>News</a>
<a href="/spotify" {% if request.path.startswith('/spotify') %}class="active"{% endif %}>Spotify</a>
```

- [ ] **Step 6: Commit**

```bash
git add web/app.py web/templates/stocks.html web/templates/news.html web/templates/base.html
git commit -m "feat: add stocks and news web UI config pages"
```

---

## Task 10: Web UI — Spotify OAuth

**Files:**
- Create: `web/templates/spotify.html`
- Modify: `web/app.py`

- [ ] **Step 1: Add Spotify OAuth routes to web/app.py**

```python
import base64 as _b64

_SPOTIFY_TOKEN_PATH = _BASE / "data" / "spotify_token.json"
_SPOTIFY_CREDS_PATH = _BASE / "data" / "spotify_credentials.json"
_SPOTIFY_SCOPES = "user-read-currently-playing user-read-playback-state"
_SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


def _spotify_connected() -> str | None:
    if not _SPOTIFY_TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(_SPOTIFY_TOKEN_PATH.read_text())
        return data.get("display_name") or data.get("email") or "Connected"
    except Exception:
        return None


@app.route("/spotify", methods=["GET", "POST"])
def spotify():
    cfg = _load_config()
    if request.method == "POST":
        cfg["spotify_enabled"] = "spotify_enabled" in request.form
        _save_config(cfg)
        try:
            _restart_display()
            flash("Spotify settings saved.", "success")
        except RuntimeError:
            flash("Settings saved but display restart failed.", "warning")
        return redirect(url_for("spotify"))
    connected = _spotify_connected()
    return render_template("spotify.html", cfg=cfg, spotify_connected=connected)


@app.route("/spotify/oauth/start")
def spotify_oauth_start():
    if not _SPOTIFY_CREDS_PATH.exists():
        flash("spotify_credentials.json not found on the server.", "danger")
        return redirect(url_for("spotify"))
    creds = json.loads(_SPOTIFY_CREDS_PATH.read_text())
    state = secrets.token_hex(16)
    session["spotify_oauth_state"] = state
    params = {
        "client_id": creds["client_id"],
        "response_type": "code",
        "redirect_uri": url_for("spotify_oauth_callback", _external=True),
        "scope": _SPOTIFY_SCOPES,
        "state": state,
    }
    from urllib.parse import urlencode
    return redirect(f"{_SPOTIFY_AUTH_URL}?{urlencode(params)}")


@app.route("/spotify/oauth/callback")
def spotify_oauth_callback():
    error = request.args.get("error")
    if error:
        flash(f"Spotify authorization denied: {error}", "danger")
        return redirect(url_for("spotify"))
    if request.args.get("state") != session.pop("spotify_oauth_state", None):
        flash("Authorization failed: invalid state.", "danger")
        return redirect(url_for("spotify"))
    try:
        creds = json.loads(_SPOTIFY_CREDS_PATH.read_text())
        auth = _b64.b64encode(f"{creds['client_id']}:{creds['client_secret']}".encode()).decode()
        resp = requests.post(
            _SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": request.args.get("code"),
                "redirect_uri": url_for("spotify_oauth_callback", _external=True),
            },
            headers={"Authorization": f"Basic {auth}"},
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()
        token_data["expires_at"] = int(time.time()) + token_data.get("expires_in", 3600)
        _SPOTIFY_TOKEN_PATH.write_text(json.dumps(token_data))
        flash("Spotify account authorized successfully.", "success")
    except Exception:
        _log.exception("Spotify OAuth callback failed")
        flash("Authorization failed. Please try again.", "danger")
    return redirect(url_for("spotify"))
```

- [ ] **Step 2: Create web/templates/spotify.html**

```html
{% extends "base.html" %}
{% block content %}
<h1>Spotify</h1>
<form method="post">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

  <div class="card">
    <h2>Authorization</h2>
    <div class="oauth-box">
      <div class="status">
        {% if spotify_connected %}
          <strong>Connected</strong>
          Spotify access is authorized.
        {% else %}
          <strong>Not authorized</strong>
          Connect a Spotify account to show now-playing.
        {% endif %}
      </div>
      <a href="/spotify/oauth/start" class="btn {% if spotify_connected %}btn-secondary{% else %}btn-primary{% endif %}" style="white-space:nowrap;">
        {% if spotify_connected %}Re-authorize{% else %}Authorize{% endif %}
      </a>
    </div>
    <p style="font-size:12px;color:#666;margin-top:12px;">
      Requires a free <a href="https://developer.spotify.com/dashboard" target="_blank">Spotify Developer app</a>.
      Add <code>{{ request.host_url }}spotify/oauth/callback</code> as a Redirect URI.
      Save <code>client_id</code> and <code>client_secret</code> to <code>data/spotify_credentials.json</code>:
      <code>{"client_id": "...", "client_secret": "..."}</code>
    </p>
  </div>

  <div class="card">
    <h2>Settings</h2>
    <div class="form-group">
      <label for="spotify_enabled">
        <input type="checkbox" id="spotify_enabled" name="spotify_enabled"
          {% if cfg.spotify_enabled %}checked{% endif %}>
        Enable Spotify page
      </label>
    </div>
  </div>

  <button type="submit" class="btn btn-primary">Save &amp; Restart Display</button>
</form>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add web/app.py web/templates/spotify.html
git commit -m "feat: add Spotify OAuth flow and config UI"
```

---

## Task 11: Full test suite + final verification

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 2: Verify config.example.json completeness**

Confirm all new fields are present with sensible defaults.

- [ ] **Step 3: Final commit**

```bash
git add -u
git commit -m "feat: Spec B complete — stocks, news, spotify pages"
```
