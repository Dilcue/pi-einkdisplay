# data/cats.py
import io
import logging
from dataclasses import dataclass

import numpy as np
import requests
from PIL import Image

_log = logging.getLogger(__name__)

_API_URL = "https://api.thecatapi.com/v1/images/search"
_USER_AGENT = "pi-einkdisplay/1.0"
_BODY_W = 800
_BODY_H = 376  # DISPLAY_H(480) - BODY_TOP(104)

# Dither to closest of: black, white, red
_PALETTE = np.array([[0, 0, 0], [255, 255, 255], [255, 0, 0]], dtype=np.float32)


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
    """Floyd-Steinberg dither img to the 3-color palette, return as RGB."""
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    H, W = arr.shape[:2]
    for y in range(H):
        for x in range(W):
            old = arr[y, x].copy()
            dists = np.sum((_PALETTE - old) ** 2, axis=1)
            ci = int(np.argmin(dists))
            new = _PALETTE[ci]
            arr[y, x] = new
            err = old - new
            if x + 1 < W:
                arr[y, x + 1] += err * 7 / 16
            if y + 1 < H:
                if x - 1 >= 0:
                    arr[y + 1, x - 1] += err * 3 / 16
                arr[y + 1, x] += err * 5 / 16
                if x + 1 < W:
                    arr[y + 1, x + 1] += err * 1 / 16
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")


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
