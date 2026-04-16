# pages/dashboard.py
from PIL import ImageDraw

from config import settings
from pages.base import (
    AppData, Page,
    WHITE, RED,
    BODY_TOP, DISPLAY_W, DISPLAY_H,
    load_font, draw_temp,
)

_F_EVT  = load_font(str(settings.fonts_dir / "notkia.ttf"), 18)
_F_STRIP_DAY  = load_font(str(settings.fonts_dir / "notkia.ttf"), 18)
_F_STRIP_ICON = load_font(str(settings.fonts_dir / "icons.ttf"), 52)
_F_STRIP_TEMP = load_font(str(settings.fonts_dir / "notkia.ttf"), 20)
_F_STRIP_COND = load_font(str(settings.fonts_dir / "notkia.ttf"), 14)
_F_EMPTY      = load_font(str(settings.fonts_dir / "notkia.ttf"), 14)

_STRIP_H    = 121
_STRIP_TOP  = DISPLAY_H - _STRIP_H           # 359
_EVENTS_H   = _STRIP_TOP - BODY_TOP          # 255 — exactly divisible by 5
_EVENT_COUNT = 5
_EVENT_H    = _EVENTS_H // _EVENT_COUNT      # 51
_PAD_X      = 16
_TIME_COL_W = DISPLAY_W // 2                 # 400 — left half
_NAME_X     = _TIME_COL_W                    # 400 — right half starts here
_MAX_TIME_W = _TIME_COL_W - _PAD_X * 2      # ~368px
_MAX_NAME_W = DISPLAY_W - _NAME_X - _PAD_X  # ~384px


def _truncate(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> str:
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…"


def _draw_events(draw: ImageDraw.ImageDraw, events: list) -> None:
    for i in range(_EVENT_COUNT):
        y = BODY_TOP + i * _EVENT_H
        text_y = y + (_EVENT_H - 22) // 2
        if i > 0:
            draw.rectangle([(0, y), (DISPLAY_W, y + 1)], fill=RED)

        if i < len(events):
            ev = events[i]
            time_text = _truncate(draw, ev.time_display, _F_EVT, _MAX_TIME_W)
            draw.text((_PAD_X, text_y), time_text, font=_F_EVT, fill=RED)
            name_text = _truncate(draw, ev.summary, _F_EVT, _MAX_NAME_W)
            draw.text((_NAME_X + _PAD_X, text_y), name_text, font=_F_EVT, fill=RED)
        else:
            draw.text((_PAD_X, text_y), "—", font=_F_EVT, fill=RED)


def _draw_forecast_strip(draw: ImageDraw.ImageDraw, w) -> None:
    draw.rectangle([(0, _STRIP_TOP), (DISPLAY_W, _STRIP_TOP + 2)], fill=RED)

    col_w  = DISPLAY_W // 5
    days   = [w.today, w.tomorrow, w.day3, w.day4, w.day5]
    labels = ["Today", w.tomorrow.day, w.day3.day, w.day4.day, w.day5.day]
    unit   = "C" if settings.use_celsius else "F"

    for i, (day, label) in enumerate(zip(days, labels)):
        x = i * col_w
        if i > 0:
            draw.rectangle([(x, _STRIP_TOP + 2), (x + 2, DISPLAY_H)], fill=RED)
        draw.text((x + 6, _STRIP_TOP + 4),           label,    font=_F_STRIP_DAY,  fill=RED)
        draw.text((x + col_w // 2, _STRIP_TOP + 26), day.icon, font=_F_STRIP_ICON, fill=RED, anchor="mt")
        draw_temp(draw, x + 6, _STRIP_TOP + 82, day.temp, unit, _F_STRIP_TEMP, RED, r=2, gap_num=-3, gap_unit=4, cy_off=2, stroke=1)
        draw.text((x + 6, _STRIP_TOP + 104),          day.cond, font=_F_STRIP_COND, fill=RED)


class DashboardPage(Page):
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        events = data.calendar_events or []
        _draw_events(draw, events)

        if data.weather is not None:
            _draw_forecast_strip(draw, data.weather)
        else:
            draw.text((_PAD_X, _STRIP_TOP + 4), "Weather unavailable", font=_F_EMPTY, fill=RED)
