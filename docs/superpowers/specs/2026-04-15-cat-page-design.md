# Cat Page Feature — Design Spec

**Date:** 2026-04-15
**Branch:** `feature/cat-page`

---

## Overview

On SW1 press from the dashboard, the display switches to a full-screen BWR (black/white/red) cat image fetched from TheCatAPI. The cat stays visible for 60 seconds or until a button is pressed. SW1 fetches a new cat; SW2 returns to the dashboard.

---

## Button Roles (Fixed)

| Button | Pin | Dashboard | Cat Mode |
|--------|-----|-----------|----------|
| SW1 | GPIO 5 | Enter cat mode | Show new cat |
| SW2 | GPIO 6 | (ignored) | Return to dashboard |

SW2 press or 60-second timeout both return to dashboard and trigger a data refresh.

---

## State Machine

```
DASHBOARD ──[SW1]──► CAT MODE ──[SW2 or 60s]──► DASHBOARD
                        │
                     [SW1] (self-loop)
                        │
                    new cat image
```

---

## Components

### `data/cat_client.py` (new)

- Fetches `https://api.thecatapi.com/v1/images/search` (no API key required)
- Downloads the returned image URL
- Resizes to 800×480 with center-crop (fill, no letterbox)
- Converts to BWR via luminance threshold:
  - Grayscale > 160 → white `(255, 255, 255)`
  - Grayscale 70–160 → red `(255, 0, 0)`
  - Grayscale < 70 → black `(0, 0, 0)`
- Returns a PIL `Image` in RGB mode
- Raises `RuntimeError` on network or decode failure (caller handles)

### `buttons.py` (addition)

New public function:

```python
def wait_for_button(timeout: float) -> int | None:
    """Block up to timeout seconds. Returns pin number (5 or 6) or None on timeout."""
```

Existing `wait_or_advance(seconds)` is refactored to call `wait_for_button()` internally, keeping its existing return type (`bool`).

The background watcher thread is updated to record *which* pin fired, not just that a press occurred. Uses a `queue.Queue` so multiple rapid presses don't collide.

### `main.py` (additions)

**Dashboard loop change:**
Replace `buttons.wait_or_advance(refresh_interval)` with `buttons.wait_for_button(refresh_interval)`. Branch on result:
- `5` → call `cat_mode()`
- `6` → ignored (no-op from dashboard)
- `None` → normal refresh cycle continues

**`cat_mode()` function:**

```
def cat_mode():
    fetch + convert cat image
    if fetch fails: show "No cats available" for 3s, return
    display cat full-screen
    start daemon thread to pre-fetch next cat

    loop:
        pin = wait_for_button(60)
        if pin == 5 or pin is None (timeout):
            if pin == 5:  # SW1
                use pre-fetched image if ready, else fetch live
                display new cat
                start daemon thread to pre-fetch next cat
            else:  # timeout
                return
        if pin == 6:  # SW2
            return

    on return: force dashboard refresh (reset last_fp to None)
```

### Pre-fetch thread

A `threading.Thread(daemon=True)` is started after each cat display. It fetches and converts the next cat image and stores the result in a shared variable (`_next_cat: Image | None`) guarded by a `threading.Lock`. On SW1, the cat mode function checks if the result is ready; if not, it fetches live (blocking briefly).

---

## Error Handling

| Failure | Behaviour |
|---------|-----------|
| TheCatAPI unreachable | Draw "No cats available" in red text, return to dashboard after 3s |
| Image decode failure | Same as above |
| Pre-fetch thread fails | Silently discarded; next SW1 press triggers live fetch |

---

## BWR Conversion

Fast luminance threshold using PIL's `point()` — no dithering loop. Steps:
1. `img.convert("L")` → grayscale
2. Apply `point()` lookup table: 256-entry map of grey → one of three RGB tuples
3. Convert result back to `"RGB"`

Expected runtime on Pi 4: < 500ms for an 800×480 image.

---

## Testing

- `tests/test_cat_client.py` — mock HTTP responses (success, 404, timeout, bad image data); verify output image dimensions and that all three pixel values are present
- `tests/test_buttons.py` — unit test `wait_for_button()` with a mock queue
- `main.py` cat mode is integration-level; covered by smoke test in simulate mode

---

## Out of Scope

- Favorite/save a cat
- Cat API key / breed filtering
- Sound
