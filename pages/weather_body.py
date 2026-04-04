# pages/weather_body.py
from PIL import ImageFont, ImageDraw

from config import settings
from pages.base import AppData, Page, BLACK, WHITE, RED, BODY_TOP, DISPLAY_W, DISPLAY_H, draw_page_dots, load_font

_SECTION_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 24)
_GLYPH_BIG_FONT = load_font(str(settings.fonts_dir / "CD-IconsPC.ttf"), 150)
_LABEL_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 14)
_VALUE_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 22)
_TEMP_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 80)
_COND_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 26)
_STRIP_DAY_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 18)
_STRIP_GLYPH_FONT = load_font(str(settings.fonts_dir / "CD-IconsPC.ttf"), 52)
_STRIP_TEMP_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 20)
_STRIP_COND_FONT = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 14)

_PAD_X = 24
_PAD_Y = 20
# Three-column layout: temp | glyph | details
_COL1_X = 24          # temp column left edge
_COL2_X = 275         # glyph column left edge (150px glyph centered ~350)
_COL3_X = 510         # details column left edge
_STRIP_H = 120
_STRIP_TOP = BODY_TOP + (480 - BODY_TOP - _STRIP_H)  # 360


def _draw_forecast_strip(draw: ImageDraw.ImageDraw, w) -> None:
    # Top border
    draw.rectangle([(0, _STRIP_TOP), (DISPLAY_W, _STRIP_TOP + 3)], fill=BLACK)

    col_w = DISPLAY_W // 5
    days = [w.today, w.tomorrow, w.day3, w.day4, w.day5]
    labels = ["Today", w.tomorrow.day, w.day3.day, w.day4.day, w.day5.day]

    for i, (day, label) in enumerate(zip(days, labels)):
        x = i * col_w
        if i > 0:
            draw.rectangle([(x, _STRIP_TOP + 3), (x + 2, DISPLAY_H)], fill=BLACK)

        # Day name
        draw.text((x + 6, _STRIP_TOP + 4), label, font=_STRIP_DAY_FONT, fill=BLACK)
        # Condition glyph — centered horizontally, centered vertically between day name and temp row
        draw.text((x + col_w // 2, _STRIP_TOP + 28), day.icon, font=_STRIP_GLYPH_FONT, fill=BLACK, anchor="mt")
        # High/low (red)
        draw.text((x + 4, _STRIP_TOP + 82), f"{day.temp}°", font=_STRIP_TEMP_FONT, fill=RED)
        # Condition text
        draw.text((x + 4, _STRIP_TOP + 104), day.cond, font=_STRIP_COND_FONT, fill=BLACK)


class WeatherBodyPage(Page):
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        if data.weather is None:
            draw.text((_PAD_X, BODY_TOP + 40), "Weather unavailable", font=_LABEL_FONT, fill=BLACK)
            draw_page_dots(draw, active_index=data.body_page_index, total=data.total_body_pages)
            return

        w = data.weather

        # Layout: label at top, then center glyph+details block in remaining space above strip
        label_y = BODY_TOP + _PAD_Y
        draw.text((_PAD_X, label_y), "WEATHER", font=_SECTION_FONT, fill=RED)

        # Vertically center content in body above the strip
        content_top = label_y + 34
        content_bottom = _STRIP_TOP - 42
        content_mid = (content_top + content_bottom) // 2

        # Col 1: current temp, right-aligned to col boundary, vertically centered
        draw.text((_COL2_X - 10, content_mid - 45), f"{w.current_temp}°", font=_TEMP_FONT, fill=RED, anchor="rt")

        # Col 2: glyph, horizontally and vertically centered in its column
        glyph_col_mid = (_COL2_X + _COL3_X) // 2
        glyph_y = content_mid - 75
        draw.text((glyph_col_mid, glyph_y), w.current_icon, font=_GLYPH_BIG_FONT, fill=BLACK, anchor="mt")

        # Col 3: Wind / Sunrise / Sunset, vertically centered as a block
        row_gap = 38
        block_h = 3 * row_gap
        detail_y = content_mid - block_h // 2
        for label, value in [
            ("Wind", f"{w.current_wind_speed} mph {w.current_wind_dir}"),
            ("Sunrise", w.current_sunrise),
            ("Sunset", w.current_sunset),
        ]:
            draw.text((_COL3_X, detail_y), label, font=_LABEL_FONT, fill=BLACK)
            draw.text((_COL3_X, detail_y + 16), value, font=_VALUE_FONT, fill=BLACK)
            detail_y += row_gap

        # Conditions centered on page just above the forecast strip
        cond_str = f"{w.current_desc.capitalize()}, feels like {w.current_feels_like}°F"
        draw.text((DISPLAY_W // 2, _STRIP_TOP - 34), cond_str, font=_COND_FONT, fill=BLACK, anchor="mt")

        _draw_forecast_strip(draw, w)
        draw_page_dots(draw, active_index=data.body_page_index, total=data.total_body_pages,
                       bottom=_STRIP_TOP - 4)
