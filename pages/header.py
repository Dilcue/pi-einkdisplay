# pages/header.py
from datetime import datetime

from PIL import ImageFont, ImageDraw

from config import settings
from pages.base import AppData, BLACK, WHITE, RED, DISPLAY_W, HEADER_H, DIVIDER_H, load_font

_TIME_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 52)
_DATE_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 24)
_TEMP_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 52)
_COND_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 18)
_GLYPH_FONT = load_font(str(settings.fonts_dir / "CD-IconsPC.ttf"), 80)

_LEFT_PAD = 20
_RIGHT_PAD = 20


def render_header(draw: ImageDraw.ImageDraw, data: AppData) -> None:
    now = datetime.now()
    time_str = now.strftime("%-I:%M %p")
    date_str = now.strftime("%B %d, %Y")

    # Left: time
    draw.text((_LEFT_PAD, 4), time_str, font=_TIME_FONT, fill=BLACK)
    # Left: date below time
    draw.text((_LEFT_PAD, 62), date_str, font=_DATE_FONT, fill=BLACK)

    # Right: weather glyph + temp + condition
    if data.weather is not None:
        w = data.weather
        # Glyph (80px CD-IconsPC)
        glyph_x = DISPLAY_W - _RIGHT_PAD - 280
        draw.text((glyph_x, 4), w.current_icon, font=_GLYPH_FONT, fill=BLACK)

        # Temp (red, 52px)
        temp_x = glyph_x + 90
        draw.text((temp_x, 4), f"{w.current_temp}°", font=_TEMP_FONT, fill=RED)

        # Condition + feels like (18px, two lines below temp — both clear of divider at y=100)
        draw.text((temp_x, 58), w.current_cond, font=_COND_FONT, fill=BLACK)
        draw.text((temp_x, 76), f"Feels Like {w.current_feels_like}°", font=_COND_FONT, fill=BLACK)

    # Divider line at y=100
    draw.rectangle(
        [(0, HEADER_H), (DISPLAY_W, HEADER_H + DIVIDER_H)],
        fill=BLACK,
    )
