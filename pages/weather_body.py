# pages/weather_body.py
from PIL import ImageFont, ImageDraw

from config import settings
from pages.base import AppData, Page, BLACK, WHITE, RED, BODY_TOP, DISPLAY_W, draw_page_dots

_SECTION_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 13)
_GLYPH_BIG_FONT = ImageFont.truetype(str(settings.fonts_dir / "CD-IconsPC.ttf"), 110)
_LABEL_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 14)
_VALUE_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 22)
_COND_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 26)
_STRIP_DAY_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 15)
_STRIP_GLYPH_FONT = ImageFont.truetype(str(settings.fonts_dir / "CD-IconsPC.ttf"), 36)
_STRIP_TEMP_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 16)
_STRIP_COND_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 11)

_PAD_X = 24
_PAD_Y = 20
_STRIP_H = 110
_STRIP_TOP = BODY_TOP + (480 - BODY_TOP - _STRIP_H)  # 370
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
        draw.text((x + 6, _STRIP_TOP + 6), label, font=_STRIP_DAY_FONT, fill=BLACK)
        # Condition glyph
        draw.text((x + col_w // 2 - 18, _STRIP_TOP + 22), day.icon, font=_STRIP_GLYPH_FONT, fill=BLACK)
        # High/low (red)
        draw.text((x + 4, _STRIP_TOP + 62), f"{day.temp}°", font=_STRIP_TEMP_FONT, fill=RED)
        # Condition text
        draw.text((x + 4, _STRIP_TOP + 84), day.cond, font=_STRIP_COND_FONT, fill=BLACK)


class WeatherBodyPage(Page):
    body_page_index = 1

    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        if data.weather is None:
            draw.text((_PAD_X, BODY_TOP + 40), "Weather unavailable", font=_LABEL_FONT, fill=BLACK)
            draw_page_dots(draw, active_index=self.body_page_index, total=data.total_body_pages)
            return

        w = data.weather

        # Section label
        draw.text((_PAD_X, BODY_TOP + _PAD_Y), "WEATHER", font=_SECTION_FONT, fill=RED)

        # Large condition glyph
        glyph_y = BODY_TOP + _PAD_Y + 20
        draw.text((_PAD_X, glyph_y), w.current_icon, font=_GLYPH_BIG_FONT, fill=BLACK)

        # Detail rows
        detail_x = _PAD_X + 120
        detail_y = BODY_TOP + _PAD_Y + 30
        row_gap = 40
        for label, value in [
            ("Wind", f"{w.current_wind_speed} mph {w.current_wind_dir}"),
            ("Sunrise", w.current_sunrise),
            ("Sunset", w.current_sunset),
        ]:
            draw.text((detail_x, detail_y), label, font=_LABEL_FONT, fill=BLACK)
            draw.text((detail_x, detail_y + 16), value, font=_VALUE_FONT, fill=BLACK)
            detail_y += row_gap

        # Conditions line above strip
        cond_str = f"{w.current_desc.capitalize()} · Feels Like {w.current_feels_like}°F"
        draw.text((_PAD_X, _STRIP_TOP - 40), cond_str, font=_COND_FONT, fill=BLACK)

        _draw_forecast_strip(draw, w)
        draw_page_dots(draw, active_index=self.body_page_index, total=data.total_body_pages)
