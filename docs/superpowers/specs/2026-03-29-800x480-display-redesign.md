# 800×480 Tricolor Display Redesign

**Date:** 2026-03-29
**Hardware:** Adafruit 7.5" 800×480 e-ink bonnet (product 6396/6418)
**Colors:** Black, white, red only — no grays, no gradients
**Fonts:** Nokia FC22 (`nokiafc22.ttf`) for all text, CD-IconsPC (`CD-IconsPC.ttf`) for all glyphs

---

## Layout Architecture

### Hybrid: Persistent Header + Rotating Body

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER (100px tall, permanent)                                 │
│  Time + Date (left)          Weather glyph + Temp (right)       │
├─────────────────────────────────────────────────────────────────┤
│  BODY (380px tall, rotating)                                    │
│  Page 0: Calendar                                               │
│  Page 1: Weather                                                │
│  Page 2: Clock                                                  │
└─────────────────────────────────────────────────────────────────┘
```

The header renders on every frame. The body rotates on a timer (page_delay_seconds from config). Page indicator dots appear bottom-right of the body.

---

## Header (100px)

**Left side:**
- Time: Nokia FC22, 52px, black
- Date: Nokia FC22, 16px, black, 4px below time baseline
- No glyph

**Right side (right-aligned, items flex row):**
- Weather condition glyph: CD-IconsPC, 80px, black — uses `resolve_weather_icon()` same as today
- Current temp: Nokia FC22, 52px, **red** (`#cc0000`)
- Condition + feels like: Nokia FC22, 14px, black (e.g. `Partly Cloudy · Feels 38°`)

**Divider:** 4px solid black line at y=100

---

## Body Pages

### Page 0 — Calendar (380px)

**Layout:** flex column, space-between, padding 14px 24px

**Section label:**
- Text: `settings.calendar_display_name`
- Font: Nokia FC22, 13px, **red**, uppercase, letter-spacing 3px

**Events (5 rows):**

Each row is a flex row: `[glyph] [time/date] [title]`

- **Glyph:** CD-IconsPC, 26px, character `\xbf` (0xBF), width 40px, centered. Draw offset -3px on y-axis to correct for font baseline low-render.
- **Time/date column:** width 175px, flex-shrink 0
  - If event is **today**: Nokia FC22, **20px**, black — show time only (e.g. `2:00 PM`)
  - If event is **future**: Nokia FC22, **13px**, black — show date + time (e.g. `Mon Mar 30 9:00 AM`)
  - All-day today: `All Day` at 20px
  - All-day future: `Mon Mar 30 All Day` at 13px
- **Event title:** Nokia FC22, 22px, black

No divider lines between events.

**Page indicator dots:** 3 dots, bottom-right, 14px diameter. Active = red fill. Inactive = white fill + 2px black border. Page 0 dot is active.

**Max events:** 5 (set `calendar_max_events: 5` in config)

---

### Page 1 — Weather (380px)

**Layout:** flex column, space-between, padding 20px 24px

**Section label:** Nokia FC22, 13px, **red**, uppercase, letter-spacing 3px — text: `Weather`

**Main block (flex row, centered):**
- **Condition glyph:** CD-IconsPC, 110px, black, centered — uses `resolve_weather_icon()` for current conditions
- **Detail rows (flex column, gap 10px):**
  - `Wind` / `12 mph NW` — label 14px, value 22px
  - `Sunrise` / `06:34 AM` — label 14px, value 22px
  - `Sunset` / `07:48 PM` — label 14px, value 22px
  - Label column width: 100px

**Conditions line (centered):**
- Nokia FC22, 26px, black
- Text: `{current_desc} · Feels Like {current_feels_like}°F`

**5-day forecast strip:**
- Top border: 3px solid black
- 5 columns, equal width, vertical dividers 2px solid black (no right border on last)
- Per column (top to bottom):
  - Day name: Nokia FC22, 15px (e.g. `Today`, `Mon`, `Tue`)
  - Condition glyph: CD-IconsPC, 36px — uses `resolve_weather_icon()`
  - High/low: Nokia FC22, 16px, **red** (e.g. `48/36°`)
  - Condition text: Nokia FC22, 11px, black

**Page indicator dots:** dot 1 (index 1) active = red.

---

### Page 2 — Clock (380px)

**Layout:** flex row, centered, gap 60px, padding 16px 24px

**Analog clock (canvas 280×280px):**
- Face: circular, radius 125px, no bounding ring or frame
- **12 tick marks** on circle perimeter, radially inward:
  - Major (0, 3, 6, 9): length 20px, lineWidth 4px, black
  - Minor: length 10px, lineWidth 2px, black
- **Hour hand:** rectangular flat (angular), length r×0.5, width 6px, black
- **Minute hand:** rectangular flat (angular), length r×0.78, width 3px, black
- **Second hand:** thin needle (lineWidth 1.5px), red, extends r×0.88 forward and 22px back from center
- **Center:** 10×10px black square, 4×4px red square centered on top

**Digital block (flex column, gap 16px):**
- Day of week: Nokia FC22, 28px, **red** (e.g. `Sunday`)
- Time: Nokia FC22, 72px, black (e.g. `10:42 AM`)
- Date: Nokia FC22, 22px, black (e.g. `March 29, 2026`)

**Page indicator dots:** dot 2 (index 2) active = red.

---

## Color Reference

| Use | Value |
|---|---|
| Black | `0` (1-bit) / `#000000` |
| White | `1` (1-bit) / `#ffffff` |
| Red | CD-IconsPC red plane / `#cc0000` in mockup |

On the tricolor panel, red pixels are written to a separate red bitplane. In code, maintain two `Image.new("1", SIZE)` images — one black layer, one red layer — and write both to the framebuffer per the Adafruit bonnet driver spec.

---

## CD-IconsPC Glyph Map (known mappings)

| Char | Code | Use |
|---|---|---|
| `H` | 0x48 | Sun (day) |
| `J` | 0x4A | Moon (night) |
| `E` | 0x45 | Partly cloudy (day) |
| `D` | 0x44 | Cloudy |
| `B` | 0x42 | Rain |
| `F` | 0x46 | Thunder |
| `C` | 0x43 | Snow |
| `G` | 0x47 | Fog |
| `\xbf` | 0xBF | Calendar |

All glyph renders should be tested against the font at target size — CD-IconsPC renders ~3px lower than optical center at most sizes. Apply a -3px y offset when vertical centering is required.

---

## Display Driver Changes Required

The current `display.py` writes a single 1-bit RGBA-encoded framebuffer to `/dev/fb0`. The Adafruit 7.5" bonnet uses a different driver. Required changes:

1. **Resolution:** Update `_WIDTH = 800`, `_HEIGHT = 480`
2. **Tricolor framebuffer:** Determine Adafruit bonnet's framebuffer format (likely two separate 1-bit planes or a 2bpp format). Update `_encode()` to accept both black and red image layers.
3. **`new_image()`:** Return a tuple of two images: `(black_img, black_draw, red_img, red_draw)` or a wrapper object
4. **`splash()`:** Update to 800×480, text remains upper-left

All pages must be updated to accept the new dual-layer draw interface.

---

## Page Architecture Changes

Each page's `render()` method currently receives a single `ImageDraw`. For tricolor:

```python
# New signature
def render(self, black_draw: ImageDraw, red_draw: ImageDraw, data: AppData) -> None:
```

- Draw black content (text, glyphs, lines) on `black_draw`
- Draw red content (temps, section labels, day name, active dot) on `red_draw`
- Red pixels must NOT also appear on black layer

---

## Config Changes

Add to `config.json` / `config.example.json`:

```json
"calendar_max_events": 5
```

The web UI calendar page max_events dropdown should cap at 5 (currently 5, matches).

---

## Files to Create / Modify

| File | Action |
|---|---|
| `display.py` | Update resolution, encode for tricolor, update splash() |
| `main.py` | Pass dual draw objects to page render calls |
| `pages/base.py` | Update Page.render() signature |
| `pages/clock.py` | Full rewrite for 800×480 hybrid layout |
| `pages/weather_current.py` | Full rewrite — now weather body only (header is shared) |
| `pages/weather_forecast.py` | Merge into weather body (forecast strip) |
| `pages/calendar_page.py` | Full rewrite for new layout |
| `pages/header.py` | **New file** — renders the persistent 100px header |
| `config.example.json` | Ensure calendar_max_events defaults to 5 |

---

## Implementation Notes

- The persistent header is not a "page" — it renders on every frame before the body page renders
- Page cycling dot indicator is rendered by each body page, not the header
- The analog clock second hand should update every second. When the clock body is active, `main.py` should call `display.update()` in a tight 1-second loop instead of waiting for `page_delay_seconds`. When the clock page's display time expires, return to normal cycling. The `ClockPage` can signal this via a `tick_interval` attribute (default `None`, clock sets `1`).
- `resolve_weather_icon()` in `utils.py` is unchanged — glyph codes remain the same
- Nokia FC22 only renders cleanly at 8px and 16px on the current display; at 800×480 use larger sizes (16, 24, 28, 52, 72px) — test each size on hardware before finalising
- The `weather_forecast.py` page is superseded by the forecast strip in the weather body — remove it after migration
