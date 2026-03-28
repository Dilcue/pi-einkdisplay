from PIL.ImageDraw import ImageDraw
from PIL import ImageFont

from config import settings
from data.weather import DayForecast
from pages.base import AppData, Page

_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 8)
_HEADER_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 16)
_WEATHER_FONT = ImageFont.truetype(str(settings.fonts_dir / "CD-IconsPC.ttf"), 24)

_BLACK = 0
_ROW_HEIGHT = 32


def _draw_row(draw: ImageDraw, top: int, label: str, forecast: DayForecast) -> None:
    # 3 rows × 32px = 96px display height. Icon at 24px, fonts at bitmap-clean 8/16px.
    draw.text((0, top + 4), forecast.icon, font=_WEATHER_FONT, fill=_BLACK)
    draw.text((30, top + 0), label, font=_FONT, fill=_BLACK)
    draw.text((30, top + 8), forecast.temp, font=_HEADER_FONT, fill=_BLACK)
    draw.text((88, top + 16), forecast.cond, font=_FONT, fill=_BLACK)


class WeatherForecastPage(Page):
    def render(self, draw: ImageDraw, data: AppData) -> None:
        if data.weather is None:
            draw.text((0, 40), "Weather unavailable", font=_FONT, fill=_BLACK)
            return

        w = data.weather
        top = 0

        _draw_row(draw, top, f"Today ({w.today.day})", w.today)
        top += _ROW_HEIGHT
        _draw_row(draw, top, f"Tomorrow ({w.tomorrow.day})", w.tomorrow)
        top += _ROW_HEIGHT
        _draw_row(draw, top, w.day3.day, w.day3)
