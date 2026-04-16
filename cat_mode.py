# cat_mode.py
from __future__ import annotations

import logging
import pathlib
import threading
import time

from PIL import Image, ImageFont

import buttons
import display
from data import cat_client

_log = logging.getLogger(__name__)
_FONTS_DIR = pathlib.Path(__file__).parent / "fonts"
_TIMEOUT = 60.0


class CatMode:
    """Full-screen cat mode. SW1 cycles to the next cat; SW2 or timeout exits."""

    def __init__(self) -> None:
        self._holder: list[Image.Image] = []
        self._lock = threading.Lock()
        self._cancelled: list[bool] = []

    def enter(self, sw1: int, sw2: int) -> None:
        """Fetch a cat, display it, and loop until SW2 is pressed or timeout."""
        _log.info("Entering cat mode")
        try:
            img = cat_client.fetch()
        except RuntimeError as e:
            _log.error("Cat fetch failed: %s", e)
            self._show_error()
            return

        display.update(img)
        self._holder, self._lock, self._cancelled = self._start_prefetch()

        while True:
            pin = buttons.wait_for_button(_TIMEOUT)
            if pin == sw1:
                try:
                    img = self._get_cat()
                except RuntimeError as e:
                    _log.error("Cat fetch failed: %s", e)
                    self._show_error()
                    return
                display.update(img)
                self._cancelled.append(True)
                self._holder, self._lock, self._cancelled = self._start_prefetch()
            else:
                _log.info("Exiting cat mode (pin=%s)", pin)
                return

    def _show_error(self) -> None:
        image, draw = display.new_image()
        try:
            font = ImageFont.truetype(str(_FONTS_DIR / "notkia.ttf"), 16)
        except OSError:
            font = ImageFont.load_default()
        draw.text((20, 20), "No cats available", font=font, fill=(255, 0, 0))
        display.update(image)
        time.sleep(3)

    def _prefetch(self, holder: list, lock: threading.Lock, cancelled: list) -> None:
        try:
            img = cat_client.fetch()
            with lock:
                if not cancelled:
                    holder.clear()
                    holder.append(img)
                    _log.info("Cat pre-fetch complete")
        except Exception as e:
            _log.warning("Cat pre-fetch failed: %s", e)

    def _start_prefetch(self) -> tuple[list, threading.Lock, list]:
        holder: list = []
        lock = threading.Lock()
        cancelled: list = []
        threading.Thread(
            target=self._prefetch, args=(holder, lock, cancelled), daemon=True
        ).start()
        return holder, lock, cancelled

    def _get_cat(self) -> Image.Image:
        with self._lock:
            if self._holder:
                return self._holder[0]
        _log.info("Pre-fetch not ready — fetching live")
        return cat_client.fetch()
