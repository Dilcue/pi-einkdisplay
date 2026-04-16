# tests/test_cat_client.py
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from data.cat_client import fetch, _to_bwr, _center_crop


def _solid_jpeg(w=400, h=300, color=(128, 128, 128)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _mock_get(json_data=None, content=None):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    if json_data is not None:
        mock.json.return_value = json_data
    if content is not None:
        mock.content = content
    return mock


@patch("data.cat_client.requests.get")
def test_fetch_returns_800x480_rgb(mock_get):
    mock_get.side_effect = [
        _mock_get(json_data=[{"url": "http://example.com/cat.jpg"}]),
        _mock_get(content=_solid_jpeg()),
    ]
    img = fetch()
    assert img.size == (800, 480)
    assert img.mode == "RGB"


@patch("data.cat_client.requests.get")
def test_fetch_mid_grey_image_contains_red_pixels(mock_get):
    mock_get.side_effect = [
        _mock_get(json_data=[{"url": "http://example.com/cat.jpg"}]),
        _mock_get(content=_solid_jpeg(color=(120, 120, 120))),
    ]
    img = fetch()
    assert (255, 0, 0) in set(img.getdata())


@patch("data.cat_client.requests.get")
def test_fetch_raises_on_network_error(mock_get):
    mock_get.side_effect = Exception("connection refused")
    with pytest.raises(RuntimeError, match="Cat fetch failed"):
        fetch()


@patch("data.cat_client.requests.get")
def test_fetch_raises_on_bad_image_bytes(mock_get):
    mock_get.side_effect = [
        _mock_get(json_data=[{"url": "http://example.com/cat.jpg"}]),
        _mock_get(content=b"not an image"),
    ]
    with pytest.raises(RuntimeError, match="Cat fetch failed"):
        fetch()


def test_center_crop_produces_correct_size():
    img = Image.new("RGB", (1000, 600))
    result = _center_crop(img, (800, 480))
    assert result.size == (800, 480)


def test_center_crop_wide_source():
    img = Image.new("RGB", (2000, 400))
    result = _center_crop(img, (800, 480))
    assert result.size == (800, 480)


def test_to_bwr_dark_pixels_become_black():
    img = Image.new("RGB", (800, 480), (30, 30, 30))
    result = _to_bwr(img)
    assert result.getpixel((0, 0)) == (0, 0, 0)


def test_to_bwr_light_pixels_become_white():
    img = Image.new("RGB", (800, 480), (200, 200, 200))
    result = _to_bwr(img)
    assert result.getpixel((0, 0)) == (255, 255, 255)


def test_to_bwr_mid_pixels_become_red():
    img = Image.new("RGB", (800, 480), (120, 120, 120))
    result = _to_bwr(img)
    assert result.getpixel((0, 0)) == (255, 0, 0)


def test_to_bwr_only_pure_bwr_pixels():
    """Every output pixel must be exactly black, red, or white — no shades."""
    img = Image.new("RGB", (800, 480), (120, 120, 120))
    result = _to_bwr(img)
    allowed = {(0, 0, 0), (255, 0, 0), (255, 255, 255)}
    assert set(result.getdata()).issubset(allowed)


def test_to_bwr_output_is_rgb_800x480():
    img = Image.new("RGB", (800, 480), (100, 100, 100))
    result = _to_bwr(img)
    assert result.mode == "RGB"
    assert result.size == (800, 480)
