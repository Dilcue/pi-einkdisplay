# pages/spotify_page.py
from __future__ import annotations

from PIL import ImageDraw

from config import settings
from pages.base import (
    AppData, Page,
    BLACK, WHITE, RED,
    BODY_TOP, DISPLAY_W,
    draw_page_dots, load_font,
)

_F_LABEL  = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 18)
_F_TRACK  = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 15)
_F_ARTIST = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 10)
_F_ALBUM  = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 9)
_F_TIME   = load_font(str(settings.fonts_dir / "nokiafc22.ttf"), 8)
_F_ICON   = load_font(str(settings.fonts_dir / "CD-IconsPC.ttf"), 66)

_GREY_LIGHT = (170, 170, 170)   # progress bar background
_GREY_MID   = (102, 102, 102)   # artist, times, idle text
_GREY_DARK  = (68, 68, 68)      # album

_ART_X    = 24
_ART_SIZE = 106
_INFO_X   = _ART_X + _ART_SIZE + 20   # 150


def _fmt_ms(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class SpotifyPage(Page):
    def render(self, draw: ImageDraw.ImageDraw, data: AppData) -> None:
        sp = data.spotify

        # Section label
        draw.text((24, BODY_TOP + 4), "NOW PLAYING", font=_F_LABEL, fill=RED)
        label_bottom = BODY_TOP + 4 + 22

        # Vertically center art+info block in remaining body space
        remaining_h = (480 - label_bottom)
        art_y = label_bottom + (remaining_h - _ART_SIZE) // 2

        # Art block — solid black square
        draw.rectangle(
            [(_ART_X, art_y), (_ART_X + _ART_SIZE - 1, art_y + _ART_SIZE - 1)],
            fill=BLACK,
        )
        # Icon inside art block
        glyph = "H" if (sp and sp.playing) else "J"
        draw.text((_ART_X + 16, art_y + 14), glyph, font=_F_ICON, fill=WHITE)

        info_y = art_y
        if sp and sp.playing:
            draw.text((_INFO_X, info_y),      sp.track[:40],  font=_F_TRACK,  fill=BLACK)
            draw.text((_INFO_X, info_y + 18), sp.artist[:40], font=_F_ARTIST, fill=_GREY_MID)
            draw.text((_INFO_X, info_y + 30), sp.album[:40],  font=_F_ALBUM,  fill=_GREY_DARK)

            # Progress bar
            bar_y   = art_y + _ART_SIZE - 18
            bar_w   = DISPLAY_W - _INFO_X - 24
            draw.rectangle([(_INFO_X, bar_y), (_INFO_X + bar_w - 1, bar_y + 4)], fill=_GREY_LIGHT)
            if sp.duration_ms > 0:
                fill_w = int(bar_w * sp.progress_ms / sp.duration_ms)
                if fill_w > 0:
                    draw.rectangle([(_INFO_X, bar_y), (_INFO_X + fill_w - 1, bar_y + 4)], fill=RED)

            # Times
            draw.text((_INFO_X,               bar_y + 7), _fmt_ms(sp.progress_ms), font=_F_TIME, fill=_GREY_MID)
            dur_str = _fmt_ms(sp.duration_ms)
            dur_w = len(dur_str) * 6
            draw.text((DISPLAY_W - 24 - dur_w, bar_y + 7), dur_str, font=_F_TIME, fill=_GREY_MID)
        else:
            draw.text((_INFO_X, info_y + 28), "Nothing playing", font=_F_ARTIST, fill=_GREY_MID)

        draw_page_dots(draw, active_index=data.body_page_index, total=data.total_body_pages)
