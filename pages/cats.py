# pages/cats.py
from PIL import ImageDraw

from pages.base import AppData, Page, BODY_TOP, draw_page_dots


class CatsPage(Page):
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        if not data.cats:
            return  # blank white body — no cat available
        frame = data.cats[data.cat_index % len(data.cats)]
        draw._image.paste(frame.image, (0, BODY_TOP))
        draw_page_dots(draw, active_index=data.body_page_index, total=data.total_body_pages)
