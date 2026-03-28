from PIL.ImageDraw import ImageDraw
from PIL import ImageFont

from config import settings
from pages.base import AppData, Page

_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 8)
_HEADER_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 12)
_WEATHER_FONT = ImageFont.truetype(str(settings.fonts_dir / "CD-IconsPC.ttf"), 32)

_BLACK = 0
_TOP = -2


class CalendarPage(Page):
    time_bonus = 1

    def render(self, draw: ImageDraw, data: AppData) -> None:
        draw.text((0, _TOP + 2), settings.calendar_display_name, font=_HEADER_FONT, fill=_BLACK)
        draw.line([(0, _TOP + 16), (200, _TOP + 16)], fill=_BLACK)

        events = data.calendar_events

        if not events:
            draw.text((34, 25), "No upcoming events!", font=_FONT, fill=_BLACK)
            return

        y = 20
        for event in events:
            draw.text((0, y - 13), "\xbf", font=_WEATHER_FONT, fill=_BLACK)  # calendar icon
            draw.text((30, y), event.time_display, font=_FONT, fill=_BLACK)
            y += 11
            draw.text((30, y), event.summary, font=_FONT, fill=_BLACK)
            y += 16
