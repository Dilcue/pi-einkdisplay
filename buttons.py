import logging
import threading
import datetime
import time
import gpiod
from gpiod.line import Bias, Edge

_PINS = [21, 16, 20, 19, 26]  # SW1–SW5
_CHIP = "/dev/gpiochip0"
_advance = threading.Event()
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
                    _advance.set()
        except Exception as e:
            _log.error("Button watcher failed: %s — retrying in 5s", e)
            time.sleep(5)


def init() -> None:
    global _thread
    _thread = threading.Thread(target=_watch, daemon=True)
    _thread.start()


def wait_or_advance(seconds: float) -> bool:
    """Sleep up to `seconds`. Returns True if a button was pressed early."""
    # Clear any press that arrived during the previous render cycle before waiting,
    # so stale events don't skip the next page immediately.
    _advance.clear()
    fired = _advance.wait(timeout=seconds)
    _advance.clear()
    return fired
