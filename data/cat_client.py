# data/cat_client.py
from __future__ import annotations

import io
import logging

import requests
from PIL import Image

_API_URL = "https://api.thecatapi.com/v1/images/search"
_DISPLAY_SIZE = (800, 480)
_log = logging.getLogger(__name__)

# Palette for grayscale-space quantisation: luminance equivalents of black (0),
# red (76 ≈ luma of pure red), and white (255). Quantising in luma space gives
# correct perceptual distances; afterwards the indices are reassigned to the
# actual BWR colours so every pixel is pure (0,0,0), (255,0,0), or (255,255,255).
_QUANT_PALETTE: Image.Image = Image.new("P", (1, 1))
_QUANT_PALETTE.putpalette(
    [0, 0, 0,         # index 0 → black luma
     76, 76, 76,      # index 1 → red luma
     255, 255, 255,   # index 2 → white luma
     ] + [0] * (256 - 3) * 3
)
_BWR_PALETTE_FLAT = [0, 0, 0, 255, 0, 0, 255, 255, 255] + [0] * (256 - 3) * 3


def fetch() -> Image.Image:
    """Fetch a random cat image and return an 800×480 black/red/white PIL Image.

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
    """Resize to 800×480 with center-crop, then dither to pure black/red/white."""
    img = img.convert("RGB")
    img = _center_crop(img, _DISPLAY_SIZE)
    # Dither in grayscale luminance space so colour distances are perceptually
    # correct (red sits at luma 76, not equidistant in RGB from black/white).
    grey_rgb = img.convert("L").convert("RGB")
    dithered = grey_rgb.quantize(
        palette=_QUANT_PALETTE, dither=Image.Dither.FLOYDSTEINBERG
    )
    # Replace the grayscale quantisation levels with actual BWR colours.
    dithered.putpalette(_BWR_PALETTE_FLAT)
    return dithered.convert("RGB")


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
