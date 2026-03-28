import threading
import gpiod
from gpiod.line import Bias, Edge

_PINS = [21, 16, 20, 19, 26]  # SW1–SW5
_CHIP = "/dev/gpiochip0"
_advance = threading.Event()
_thread = None


def _watch():
    request = gpiod.request_lines(
        _CHIP,
        consumer="einkdisplay-buttons",
        config={
            tuple(_PINS): gpiod.LineSettings(
                edge_detection=Edge.FALLING,
                bias=Bias.PULL_UP,
                debounce_period=__import__("datetime").timedelta(milliseconds=300),
            )
        },
    )
    while True:
        if request.wait_edge_events(timeout=__import__("datetime").timedelta(seconds=1)):
            request.read_edge_events()
            _advance.set()


def init() -> None:
    global _thread
    _thread = threading.Thread(target=_watch, daemon=True)
    _thread.start()


def wait_or_advance(seconds: float) -> bool:
    """Sleep up to `seconds`. Returns True if a button was pressed early."""
    fired = _advance.wait(timeout=seconds)
    _advance.clear()
    return fired
