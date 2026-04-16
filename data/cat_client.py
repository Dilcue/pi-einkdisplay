# data/cat_client.py
from __future__ import annotations

import io
import logging

import requests
from PIL import Image

_API_URL = "https://api.thecatapi.com/v1/images/search"
_DISPLAY_SIZE = (800, 480)
_log = logging.getLogger(__name__)

_WHITE_THRESHOLD = 160
_BLACK_THRESHOLD = 70

# 768-entry lookup table for PIL Image.point(lut, "RGB") on a grayscale "L" image.
# PIL expects separate channel blocks: 256 R values, then 256 G values, then 256 B values.
# Thresholds: < _BLACK_THRESHOLD → black, > _WHITE_THRESHOLD → white, else → red.
_LUT: list[int] = (
    # R channel: black=0, red=255, white=255
    [0 if _v < _BLACK_THRESHOLD else 255 for _v in range(256)]
    # G channel: black=0, red=0, white=255
    + [0 if _v <= _WHITE_THRESHOLD else 255 for _v in range(256)]
    # B channel: black=0, red=0, white=255
    + [0 if _v <= _WHITE_THRESHOLD else 255 for _v in range(256)]
)


def fetch() -> Image.Image:
    """Fetch a random cat image and return an 800×480 BWR PIL Image.

    Raises RuntimeError on any network or decode failure.
    """
    try:
        resp = requests.get(_API_URL, timeout=10)
        resp.raise_for_status()
        img_url = resp.json()[0]["url"]
        img_resp = requests.get(img_url, timeout=15)
        img_resp.raise_for_status()
        img = Image.open(io.BytesIO(img_resp.content))
        img.load()  # force decode before BytesIO is discarded
    except Exception as e:
        raise RuntimeError(f"Cat fetch failed: {e}") from e

    return _to_bwr(img)


def _to_bwr(img: Image.Image) -> Image.Image:
    """Resize to 800×480 with center-crop, then apply BWR threshold conversion."""
    img = img.convert("RGB")
    img = _center_crop(img, _DISPLAY_SIZE)
    grey = img.convert("L")
    return grey.point(_LUT, "RGB")


def _center_crop(img: Image.Image, target: tuple[int, int]) -> Image.Image:
    """Scale image to fill target dimensions, then center-crop to exact size."""
    tw, th = target
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - tw) // 2
    top = (new_h - th) // 2
    return img.crop((left, top, left + tw, top + th))
