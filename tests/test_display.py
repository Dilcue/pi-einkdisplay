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
