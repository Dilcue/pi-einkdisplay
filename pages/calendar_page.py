# pages/calendar_page.py
from PIL import ImageFont, ImageDraw

from config import settings
from pages.base import AppData, Page, BLACK, WHITE, RED, BODY_TOP, draw_page_dots

_SECTION_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 13)
_GLYPH_FONT = ImageFont.truetype(str(settings.fonts_dir / "CD-IconsPC.ttf"), 26)
_TIME_TODAY_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 20)
_TIME_FUTURE_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 13)
_TITLE_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 22)
_EMPTY_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 22)

_PAD_X = 24
_PAD_Y = 14
_GLYPH_W = 40
_TIME_COL_W = 175
_ROW_H = 62
_GLYPH_Y_OFFSET = -3  # CD-IconsPC renders ~3px low

_TODAY_PREFIXES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class CalendarPage(Page):
    body_page_index = 0

    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        draw.text((_PAD_X, BODY_TOP + _PAD_Y), settings.calendar_display_name.upper(),
                  font=_SECTION_FONT, fill=RED)

        events = data.calendar_events or []

        if not events:
            draw.text((_PAD_X, BODY_TOP + 60), "No upcoming events!", font=_EMPTY_FONT, fill=BLACK)
            draw_page_dots(draw, active_index=self.body_page_index, total=data.total_body_pages)
            return

        y = BODY_TOP + _PAD_Y + 24
        for event in events[:5]:
            time_x = _PAD_X + _GLYPH_W
            title_x = time_x + _TIME_COL_W

            draw.text((_PAD_X, y + _GLYPH_Y_OFFSET), "\xbf", font=_GLYPH_FONT, fill=BLACK)

            is_today = not event.time_display.startswith(_TODAY_PREFIXES)
            time_font = _TIME_TODAY_FONT if is_today else _TIME_FUTURE_FONT
            draw.text((time_x, y), event.time_display, font=time_font, fill=BLACK)
            draw.text((title_x, y), event.summary, font=_TITLE_FONT, fill=BLACK)

            y += _ROW_H

        draw_page_dots(draw, active_index=self.body_page_index, total=data.total_body_pages)
