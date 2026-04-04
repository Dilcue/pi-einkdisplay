# tests/test_display.py
import os
import pytest

os.environ["EINK_SIMULATE"] = "1"

import display


def test_new_image_returns_800x480_rgb():
    image, draw = display.new_image()
    assert image.size == (800, 480)
    assert image.mode == "RGB"


def test_update_saves_png_in_simulator_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("EINK_SIMULATE", "1")
    preview_path = tmp_path / "preview.png"
    monkeypatch.setattr(display, "_PREVIEW_PATH", str(preview_path))
    image, _ = display.new_image()
    display.update(image)
    assert preview_path.exists()


def test_init_in_simulator_mode_is_noop():
    # _display should remain None after init() in simulator mode
    import display as d
    d._display = None
    d.init()
    assert d._display is None


def test_clear_saves_white_png(tmp_path, monkeypatch):
    monkeypatch.setenv("EINK_SIMULATE", "1")
    preview_path = tmp_path / "preview.png"
    monkeypatch.setattr(display, "_PREVIEW_PATH", str(preview_path))
    display.clear()
    assert preview_path.exists()
    from PIL import Image
    img = Image.open(str(preview_path))
    assert img.size == (800, 480)


# --- pages/base.py tests ---

from pages.base import BLACK, WHITE, RED, BODY_TOP, draw_page_dots, AppData
from PIL import Image, ImageDraw as PILImageDraw


def test_color_constants_are_rgb_tuples():
    assert BLACK == (0, 0, 0)
    assert WHITE == (255, 255, 255)
    assert RED == (255, 0, 0)


def test_body_top_is_104():
    assert BODY_TOP == 104


def test_draw_page_dots_no_crash():
    image = Image.new("RGB", (800, 480), WHITE)
    draw = PILImageDraw.Draw(image)
    draw_page_dots(draw, active_index=1, total=3)  # should not raise


def test_appdata_page_fields():
    data = AppData()
    assert data.body_page_index == 0
    assert data.total_body_pages == 3
