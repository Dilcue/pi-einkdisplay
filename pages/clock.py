# pages/clock.py
import math
from datetime import datetime

from PIL import ImageFont, ImageDraw

from config import settings
from pages.base import AppData, Page, BLACK, WHITE, RED, BODY_TOP, draw_page_dots, load_font

_DAY_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 28)
_TIME_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 72)
_DATE_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 28)

_PAD_X = 24
_PAD_Y = 16
_CLOCK_SIZE = 280
_CLOCK_R = 125
_GAP = 60

_CX = _PAD_X + _CLOCK_SIZE // 2        # 164
_BODY_CENTER_Y = (BODY_TOP + 480) // 2  # 292
_CY = _BODY_CENTER_Y                    # analog clock centered in body

_DIG_X = _PAD_X + _CLOCK_SIZE + _GAP   # 364

# Vertically center the digital block in the body area.
# Block spans: day(0) → time(+40) → date(+120), bottom ≈ +146px
# Body center = BODY_TOP + (480 - BODY_TOP) // 2 = 292
_DIG_Y = (BODY_TOP + (480 - BODY_TOP) // 2) - 73  # 219


def _hand_polygon(cx: int, cy: int, length: float, width: float, angle_rad: float) -> list:
    """Return 4 corners of a clock hand rectangle."""
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    hw = width / 2
    return [
        (int(cx + cos_a * hw), int(cy + sin_a * hw)),
        (int(cx - cos_a * hw), int(cy - sin_a * hw)),
        (int(cx - cos_a * hw + sin_a * length), int(cy - sin_a * hw - cos_a * length)),
        (int(cx + cos_a * hw + sin_a * length), int(cy + sin_a * hw - cos_a * length)),
    ]


def _draw_analog_clock(draw: ImageDraw.ImageDraw, now: datetime) -> None:
    cx, cy = _CX, _CY
    r = _CLOCK_R

    # Tick marks
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        is_major = i % 3 == 0
        tick_len = 20 if is_major else 10
        tick_w = 4 if is_major else 2
        ox = cx + r * math.cos(angle)
        oy = cy + r * math.sin(angle)
        ix = cx + (r - tick_len) * math.cos(angle)
        iy = cy + (r - tick_len) * math.sin(angle)
        draw.line([(ox, oy), (ix, iy)], fill=BLACK, width=tick_w)

    # Hour hand
    hour_angle = math.radians((now.hour % 12) * 30 + now.minute * 0.5 - 90)
    draw.polygon(_hand_polygon(cx, cy, r * 0.5, 6, hour_angle), fill=BLACK)

    # Minute hand
    min_angle = math.radians(now.minute * 6 + now.second * 0.1 - 90)
    draw.polygon(_hand_polygon(cx, cy, r * 0.78, 3, min_angle), fill=BLACK)

    # Second hand — commented out until hardware arrives for tuning
    # sec_angle = math.radians(now.second * 6 - 90)
    # sec_tip_x = int(cx + r * 0.88 * math.cos(sec_angle))
    # sec_tip_y = int(cy + r * 0.88 * math.sin(sec_angle))
    # sec_tail_x = int(cx - 22 * math.cos(sec_angle))
    # sec_tail_y = int(cy - 22 * math.sin(sec_angle))
    # draw.line([(sec_tail_x, sec_tail_y), (sec_tip_x, sec_tip_y)], fill=RED, width=2)

    # Center: 10×10 black square, 4×4 red square on top
    draw.rectangle([(cx - 5, cy - 5), (cx + 5, cy + 5)], fill=BLACK)
    draw.rectangle([(cx - 2, cy - 2), (cx + 2, cy + 2)], fill=RED)


class ClockPage(Page):
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        now = datetime.now()
        _draw_analog_clock(draw, now)

        day_str = now.strftime("%A")
        time_str = now.strftime("%-I:%M %p")
        date_str = now.strftime("%B %-d, %Y")

        draw.text((_DIG_X, _DIG_Y), day_str, font=_DAY_FONT, fill=RED)
        draw.text((_DIG_X, _DIG_Y + 40), time_str, font=_TIME_FONT, fill=BLACK)
        draw.text((_DIG_X, _DIG_Y + 120), date_str, font=_DATE_FONT, fill=BLACK)

        draw_page_dots(draw, active_index=data.body_page_index, total=data.total_body_pages)
