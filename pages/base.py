from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from PIL.ImageDraw import ImageDraw

from data.weather import WeatherReport
from data.calendar_client import CalendarEvent


@dataclass
class AppData:
    weather: WeatherReport | None = None
    calendar_events: list[CalendarEvent] | None = None


class Page(ABC):
    time_bonus: int = 0

    @abstractmethod
    def render(self, draw: ImageDraw, data: AppData) -> None:
        """Draw this page. draw = ImageDraw instance, data = AppData."""
        pass
