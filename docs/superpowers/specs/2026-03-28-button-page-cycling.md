# Button Page Cycling — Design Spec

**Date:** 2026-03-28
**Status:** Approved

---

## Overview

Add immediate page cycling to any of the 5 Papirus HAT buttons (SW1–SW5). Pressing any button advances to the next page without waiting for the current page's timer to expire.

---

## Design

### New module: `buttons.py`

Owns all GPIO setup and interrupt registration. Exposes a single `wait_or_advance(seconds)` function used by the main loop.

```python
import RPi.GPIO as GPIO
import threading

_PINS = [21, 16, 20, 19, 26]  # SW1–SW5
_advance = threading.Event()

def _on_press(channel):
    _advance.set()

def init():
    GPIO.setmode(GPIO.BCM)
    for pin in _PINS:
        GPIO.setup(pin, GPIO.IN)
        GPIO.add_event_detect(pin, GPIO.FALLING, callback=_on_press, bouncetime=300)

def wait_or_advance(seconds: float) -> bool:
    """Sleep up to `seconds`. Returns True if a button was pressed early."""
    fired = _advance.wait(timeout=seconds)
    _advance.clear()
    return fired
```

### Changes to `main.py`

- Import `buttons`
- Call `buttons.init()` after `display.init()`
- Replace `time.sleep(settings.page_delay_seconds + page.time_bonus)` with `buttons.wait_or_advance(settings.page_delay_seconds + page.time_bonus)`

No other files change.

---

## Behaviour

- Any of the 5 buttons advances to the next page immediately
- 300ms debounce prevents double-firing on a single press
- If no button is pressed, the page advances on its normal timer (unchanged)
- All buttons do the same thing (cycle forward)

---

## Out of Scope

- Individual button assignments (e.g. back, jump to page)
- Long-press behaviour
- Button LEDs or feedback
