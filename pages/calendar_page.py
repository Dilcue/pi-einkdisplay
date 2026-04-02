# pages/calendar_page.py
from PIL import ImageFont, ImageDraw

from config import settings
from pages.base import AppData, Page, BLACK, WHITE, RED, BODY_TOP, draw_page_dots, load_font

_SECTION_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 22)
_TIME_TODAY_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 22)
_TIME_FUTURE_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 18)
_TITLE_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 22)
_EMPTY_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 22)

_PAD_X = 24
_PAD_Y = 14
_TIME_COL_W = 240   # enough for "Thu Apr 3, 10:00 AM" at 18px
_TITLE_GAP = 20     # extra gap between time col and title

_TODAY_PREFIXES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class CalendarPage(Page):
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        # Label pinned to top
        label_y = BODY_TOP + _PAD_Y
        draw.text((_PAD_X, label_y), settings.calendar_display_name.upper(),
                  font=_SECTION_FONT, fill=RED)

        events = data.calendar_events or []
        title_x = _PAD_X + _TIME_COL_W + _TITLE_GAP

        if not events:
            draw.text((_PAD_X, label_y + 80), "No upcoming events!", font=_EMPTY_FONT, fill=BLACK)
            draw_page_dots(draw, active_index=data.body_page_index, total=data.total_body_pages)
            return

        # Evenly distribute events in the area below the label
        events_top = label_y + 38
        events_bottom = 458  # leave room for dots
        num = min(len(events), 5)
        slot_h = (events_bottom - events_top) // num

        for i, event in enumerate(events[:5]):
            # Vertically center text within slot
            y = events_top + i * slot_h + (slot_h - 22) // 2

            is_today = not event.time_display.startswith(_TODAY_PREFIXES)
            time_font = _TIME_TODAY_FONT if is_today else _TIME_FUTURE_FONT
            draw.text((_PAD_X, y), event.time_display, font=time_font, fill=BLACK)
            draw.text((title_x, y), event.summary, font=_TITLE_FONT, fill=BLACK)

        draw_page_dots(draw, active_index=data.body_page_index, total=data.total_body_pages)
