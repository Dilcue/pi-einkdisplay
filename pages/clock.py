from datetime import datetime

from PIL.ImageDraw import ImageDraw
from PIL import ImageFont

from config import settings
from pages.base import AppData, Page

_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 8)
_HEADER_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 12)
_HUGE_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 24)

_BLACK = 0
_TOP = -2


class ClockPage(Page):
    def render(self, draw: ImageDraw, data: AppData) -> None:
        now = datetime.now()
        current_day = now.strftime("%A")
        current_date = now.strftime("%B, %d %Y")
        current_time = now.strftime("%I:%M %p")

        draw.text((((128 - len(current_time)) / 4), _TOP + 15), current_time, font=_HUGE_FONT, fill=_BLACK)
        draw.text((((128 - len(current_day)) / 2), _TOP + 60), current_day, font=_HEADER_FONT, fill=_BLACK)
        draw.text((((128 - len(current_date)) / 2.75), _TOP + 75), current_date, font=_HEADER_FONT, fill=_BLACK)
