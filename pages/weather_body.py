# pages/weather_body.py
from PIL import ImageFont, ImageDraw

from config import settings
from pages.base import AppData, Page, BLACK, WHITE, RED, BODY_TOP, DISPLAY_W, draw_page_dots

_SECTION_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 24)
_GLYPH_BIG_FONT = ImageFont.truetype(str(settings.fonts_dir / "CD-IconsPC.ttf"), 120)
_LABEL_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 14)
_VALUE_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 22)
_COND_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 18)
_STRIP_DAY_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 18)
_STRIP_GLYPH_FONT = ImageFont.truetype(str(settings.fonts_dir / "CD-IconsPC.ttf"), 52)
_STRIP_TEMP_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 20)
_STRIP_COND_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 14)

_PAD_X = 24
_PAD_Y = 20
# Horizontal center for the glyph+detail block.
# Glyph ~150px wide, detail col offset 170px, detail text ~110px → block ~280px total.
_BLOCK_X = (DISPLAY_W - 280) // 2  # 260
_STRIP_H = 120
_STRIP_TOP = BODY_TOP + (480 - BODY_TOP - _STRIP_H)  # 360
_DISPLAY_H = 480


def _draw_forecast_strip(draw: ImageDraw.ImageDraw, w) -> None:
    # Top border
    draw.rectangle([(0, _STRIP_TOP), (DISPLAY_W, _STRIP_TOP + 3)], fill=BLACK)

    col_w = DISPLAY_W // 5
    days = [w.today, w.tomorrow, w.day3, w.day4, w.day5]
    labels = ["Today", w.tomorrow.day, w.day3.day, w.day4.day, w.day5.day]

    for i, (day, label) in enumerate(zip(days, labels)):
        x = i * col_w
        if i > 0:
            draw.rectangle([(x, _STRIP_TOP + 3), (x + 2, _DISPLAY_H)], fill=BLACK)

        # Day name
        draw.text((x + 6, _STRIP_TOP + 4), label, font=_STRIP_DAY_FONT, fill=BLACK)
        # Condition glyph
        draw.text((x + col_w // 2 - 24, _STRIP_TOP + 26), day.icon, font=_STRIP_GLYPH_FONT, fill=BLACK)
        # High/low (red)
        draw.text((x + 4, _STRIP_TOP + 82), f"{day.temp}°", font=_STRIP_TEMP_FONT, fill=RED)
        # Condition text
        draw.text((x + 4, _STRIP_TOP + 104), day.cond, font=_STRIP_COND_FONT, fill=BLACK)


class WeatherBodyPage(Page):
    body_page_index = 1

    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        if data.weather is None:
            draw.text((_PAD_X, BODY_TOP + 40), "Weather unavailable", font=_LABEL_FONT, fill=BLACK)
            draw_page_dots(draw, active_index=self.body_page_index, total=data.total_body_pages)
            return

        w = data.weather

        # Layout: label at top, then center glyph+details block in remaining space above strip
        label_y = BODY_TOP + _PAD_Y
        draw.text((_PAD_X, label_y), "WEATHER", font=_SECTION_FONT, fill=RED)

        # Glyph is ~120px tall. Center it vertically in the content area.
        # Conditions go below the glyph, constrained to left column (clear of detail at x=430).
        content_top = label_y + 34
        content_bottom = _STRIP_TOP - 42
        block_h = 120  # glyph height
        block_top = content_top + (content_bottom - content_top - block_h) // 2
        glyph_y = block_top
        draw.text((_BLOCK_X, glyph_y), w.current_icon, font=_GLYPH_BIG_FONT, fill=BLACK)

        detail_x = _BLOCK_X + 170
        detail_y = block_top + 10
        row_gap = 48
        for label, value in [
            ("Wind", f"{w.current_wind_speed} mph {w.current_wind_dir}"),
            ("Sunrise", w.current_sunrise),
            ("Sunset", w.current_sunset),
        ]:
            draw.text((detail_x, detail_y), label, font=_LABEL_FONT, fill=BLACK)
            draw.text((detail_x, detail_y + 18), value, font=_VALUE_FONT, fill=BLACK)
            detail_y += row_gap

        # Conditions below glyph, left-aligned — stays within ~130px, clear of detail column
        cond_y = glyph_y + block_h + 4
        draw.text((_BLOCK_X, cond_y), w.current_desc.capitalize(), font=_COND_FONT, fill=BLACK)
        draw.text((_BLOCK_X, cond_y + 20), f"Feels Like {w.current_feels_like}°F", font=_COND_FONT, fill=BLACK)

        _draw_forecast_strip(draw, w)
        draw_page_dots(draw, active_index=self.body_page_index, total=data.total_body_pages,
                       bottom=_STRIP_TOP - 4)
