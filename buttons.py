from __future__ import annotations

import logging
import queue
import threading
import datetime
import time
import gpiod
from gpiod.line import Bias, Edge

_PINS = [5, 6]  # SW1, SW2
_CHIP = "/dev/gpiochip0"
_press_queue: queue.Queue[int] = queue.Queue()
_thread = None
_log = logging.getLogger(__name__)


def _watch():
    while True:
        try:
            request = gpiod.request_lines(
                _CHIP,
                consumer="einkdisplay-buttons",
                config={
                    tuple(_PINS): gpiod.LineSettings(
                        edge_detection=Edge.FALLING,
                        bias=Bias.PULL_UP,
                        debounce_period=datetime.timedelta(milliseconds=300),
                    )
                },
            )
            _log.info("Button watcher started on pins %s", _PINS)
            while True:
                if request.wait_edge_events(timeout=datetime.timedelta(seconds=1)):
                    events = request.read_edge_events()
                    for e in events:
                        _log.info("Button pressed on pin %s", e.line_offset)
                        _press_queue.put(e.line_offset)
        except Exception as e:
            _log.error("Button watcher failed: %s — retrying in 5s", e)
            time.sleep(5)


def init() -> None:
    global _thread
    _thread = threading.Thread(target=_watch, daemon=True)
    _thread.start()


def wait_for_button(timeout: float) -> int | None:
    """Block up to timeout seconds. Returns pin number (5 or 6) or None on timeout."""
    try:
        return _press_queue.get(timeout=timeout)
    except queue.Empty:
        return None


def wait_or_advance(seconds: float) -> bool:
    """Sleep up to `seconds`. Returns True if a button was pressed early."""
    return wait_for_button(seconds) is not None
