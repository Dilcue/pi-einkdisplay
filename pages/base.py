# pages/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import ImageDraw, ImageFont

if TYPE_CHECKING:
    from data.weather import WeatherReport
    from data.calendar_client import CalendarEvent

def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font, falling back to the PIL default on failure."""
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


# Color palette (RGB tuples for PIL RGB images)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# Layout constants
DISPLAY_W = 800
DISPLAY_H = 480
HEADER_H = 100
DIVIDER_H = 4
BODY_TOP = HEADER_H + DIVIDER_H  # 104


@dataclass
class AppData:
    weather: WeatherReport | None = None
    calendar_events: list[CalendarEvent] | None = None


class Page(ABC):
    @abstractmethod
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        """Draw this page's body content. draw is on an 800×480 RGB image."""
        pass
