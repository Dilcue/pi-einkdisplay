from PIL.ImageDraw import ImageDraw
from PIL import ImageFont

from config import settings
from pages.base import AppData, Page

_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 8)
_HEADER_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 12)
_HUGE_FONT = ImageFont.truetype(str(settings.fonts_dir / "nokiafc22.ttf"), 24)
_BIG_WEATHER_FONT = ImageFont.truetype(str(settings.fonts_dir / "CD-IconsPC.ttf"), 48)

_BLACK = 0
_TOP = -2


class WeatherCurrentPage(Page):
    time_bonus = 1

    def render(self, draw: ImageDraw, data: AppData) -> None:
        if data.weather is None:
            draw.text((0, _TOP + 40), "Weather unavailable", font=_FONT, fill=_BLACK)
            return

        w = data.weather

        draw.text((0, _TOP + 2), "Right Now", font=_HEADER_FONT, fill=_BLACK)
        draw.text((102, _TOP + 6), f"(as of {w.last_update} update)", font=_FONT, fill=_BLACK)
        draw.line([(0, _TOP + 16), (200, _TOP + 16)], fill=_BLACK)

        draw.text((0, _TOP + 30), w.current_icon, font=_BIG_WEATHER_FONT, fill=_BLACK)

        draw.text((45, _TOP + 19), w.current_temp, font=_HUGE_FONT, fill=_BLACK)
        draw.text((90, _TOP + 22), w.current_desc.capitalize(), font=_FONT, fill=_BLACK)
        draw.text((90, _TOP + 34), f"Feels Like {w.current_feels_like}", font=_FONT, fill=_BLACK)

        draw.text((45, _TOP + 50), f"Wind Speed: {w.current_wind_speed}mph {w.current_wind_dir}", font=_FONT, fill=_BLACK)
        draw.text((45, _TOP + 60), f"Visibility: {w.current_visibility}", font=_FONT, fill=_BLACK)
        draw.text((45, _TOP + 70), f"Sunrise: {w.current_sunrise}", font=_FONT, fill=_BLACK)
        draw.text((45, _TOP + 80), f"Sunset: {w.current_sunset}", font=_FONT, fill=_BLACK)
