# data/cats.py
import io
import logging
from dataclasses import dataclass

import requests
from PIL import Image

_log = logging.getLogger(__name__)

_API_URL = "https://api.thecatapi.com/v1/images/search"
_USER_AGENT = "pi-einkdisplay/1.0"
_BODY_W = 800
_BODY_H = 376  # DISPLAY_H(480) - BODY_TOP(104)

# Palette image used by PIL's C-accelerated quantize: black, white, red
_PALETTE_IMG = Image.new("P", (1, 1))
_PALETTE_IMG.putpalette(
    [0, 0, 0,         # index 0 = black
     255, 255, 255,   # index 1 = white
     255, 0, 0]       # index 2 = red
    + [0] * (256 * 3 - 9)
)


@dataclass
class CatFrame:
    image: Image.Image  # RGB mode, 800×376


def _cover_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    new_w = round(img.width * scale)
    new_h = round(img.height * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    x = (new_w - w) // 2
    y = (new_h - h) // 2
    return img.crop((x, y, x + w, y + h))


def _dither_to_rgb(img: Image.Image) -> Image.Image:
    """Floyd-Steinberg dither img to the 3-color palette using PIL's C implementation."""
    quantized = img.convert("RGB").quantize(
        palette=_PALETTE_IMG,
        dither=Image.Dither.FLOYDSTEINBERG,
    )
    return quantized.convert("RGB")


def fetch(count: int) -> list[CatFrame]:
    """Fetch count cat images, cover-crop to 800×376, dither to tricolor. Returns list of CatFrame."""
    try:
        resp = requests.get(
            _API_URL,
            params={"limit": count},
            headers={"User-Agent": _USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json()
    except Exception as e:
        _log.error("Cat API request failed: %s", e)
        return []

    if len(items) < count:
        _log.warning("Cat API returned %d images (requested %d)", len(items), count)

    frames: list[CatFrame] = []
    for item in items:
        url = item.get("url", "")
        try:
            img_resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=15)
            img_resp.raise_for_status()
            img = Image.open(io.BytesIO(img_resp.content))
            img = _cover_crop(img, _BODY_W, _BODY_H)
            img = _dither_to_rgb(img)
            frames.append(CatFrame(image=img))
        except Exception as e:
            _log.warning("Failed to fetch/process cat image %s: %s", url, e)
            continue

    return frames
