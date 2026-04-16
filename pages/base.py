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


def draw_temp(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    temp: str,
    unit: str,
    font,
    fill,
    r: int,
    gap_num: int,
    gap_unit: int,
    cy_off: int,
    stroke: int,
) -> None:
    """Draw a temperature string followed by a hand-drawn degree circle and unit letter."""
    draw.text((x, y), temp, font=font, fill=fill)
    bb = font.getbbox(temp)
    num_w = bb[2] - bb[0]
    cx = x + num_w + gap_num + r
    cy = y + cy_off
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=fill, width=stroke)
    draw.text((cx + r + gap_unit, y), unit, font=font, fill=fill)


class Page(ABC):
    @abstractmethod
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        """Draw this page's body content. draw is on an 800×480 RGB image."""
        pass
