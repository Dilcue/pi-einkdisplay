# pages/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PIL import ImageDraw, ImageFont

if TYPE_CHECKING:
    from data.weather import WeatherReport
    from data.calendar_client import CalendarEvent
    from data.cats import CatFrame

def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font, falling back to the PIL default on failure."""
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


# Color palette (RGB tuples for PIL RGB images)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# Layout constants
DISPLAY_W = 800
DISPLAY_H = 480
HEADER_H = 100
DIVIDER_H = 4
BODY_TOP = HEADER_H + DIVIDER_H  # 104

# Page indicator dots
_DOT_D = 14
_DOT_SPACING = 22
_DOT_BORDER = 2
_DOT_RIGHT_PAD = 24
_DOT_BOTTOM_PAD = 14


def draw_page_dots(draw: ImageDraw.ImageDraw, active_index: int, total: int, bottom: int = DISPLAY_H) -> None:
    """Draw page indicator dots at bottom-right. bottom overrides the anchor row."""
    total_w = total * _DOT_D + (total - 1) * (_DOT_SPACING - _DOT_D)
    right_x = DISPLAY_W - _DOT_RIGHT_PAD
    start_x = right_x - total_w
    y = bottom - _DOT_BOTTOM_PAD - _DOT_D
    for i in range(total):
        x = start_x + i * _DOT_SPACING
        bbox = [x, y, x + _DOT_D, y + _DOT_D]
        if i == active_index:
            draw.ellipse(bbox, fill=RED)
        else:
            draw.ellipse(bbox, fill=WHITE, outline=RED, width=_DOT_BORDER)


@dataclass
class AppData:
    weather: WeatherReport | None = None
    calendar_events: list[CalendarEvent] | None = None
    cats: list[CatFrame] = field(default_factory=list)
    cat_index: int = 0
    body_page_index: int = 0
    total_body_pages: int = 3


class Page(ABC):
    time_bonus: int = 0
    body_page_index: int = 0  # override per page class

    @abstractmethod
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        """Draw this page's body content. draw is on an 800×480 RGB image."""
        pass
