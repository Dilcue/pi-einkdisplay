# pages/header.py
from datetime import datetime

from PIL import ImageFont, ImageDraw

from config import settings
from pages.base import AppData, WHITE, RED, DISPLAY_W, HEADER_H, DIVIDER_H, load_font

_DATE_FONT  = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 36)
_DAY_FONT   = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 52)
_TEMP_FONT  = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 52)
_COND_FONT  = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 18)
_GLYPH_FONT = load_font(str(settings.fonts_dir / "CD-IconsPC.ttf"), 96)

_LEFT_PAD  = 20
_RIGHT_PAD = 20


def render_header(draw: ImageDraw.ImageDraw, data: AppData) -> None:
    now = datetime.now()
    day_str  = now.strftime("%A")
    date_str = now.strftime("%B %-d, %Y")

    draw.text((_LEFT_PAD, 4),  day_str,  font=_DAY_FONT,  fill=RED)
    draw.text((_LEFT_PAD, 60), date_str, font=_DATE_FONT, fill=RED)

    if data.weather is not None:
        w = data.weather
        glyph_x = DISPLAY_W - _RIGHT_PAD - 280
        draw.text((glyph_x, HEADER_H // 2), w.current_icon, font=_GLYPH_FONT, fill=RED, anchor="lm")

        temp_x = glyph_x + 90
        draw.text((temp_x, 4),  f"{w.current_temp}°",               font=_TEMP_FONT, fill=RED)
        draw.text((temp_x, 58), w.current_cond,                      font=_COND_FONT, fill=RED)
        draw.text((temp_x, 76), f"Feels Like {w.current_feels_like}°", font=_COND_FONT, fill=RED)

    draw.rectangle([(0, HEADER_H), (DISPLAY_W, HEADER_H + DIVIDER_H)], fill=RED)
