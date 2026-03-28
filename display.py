import struct
from PIL import Image, ImageDraw

_FB_PATH = "/dev/fb0"
_WIDTH = 200
_HEIGHT = 96
_SIZE = (_WIDTH, _HEIGHT)


def init() -> None:
    # Verify framebuffer is accessible
    with open(_FB_PATH, "wb"):
        pass


def new_image() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("1", _SIZE, 1)  # 1 = white
    draw = ImageDraw.Draw(image)
    return image, draw


def _encode(image: Image.Image) -> bytes:
    """Convert a 1-bit image to the RGBA encoding the repaper DRM framebuffer expects."""
    from PIL import ImageOps
    return ImageOps.invert(image.convert("L")).convert("RGBA").tobytes()


def clear() -> None:
    """Write a full white frame to clear ghosting between page cycles."""
    white = Image.new("1", _SIZE, 1)  # 1 = white, same as new_image()
    with open(_FB_PATH, "wb") as fb:
        fb.write(_encode(white))


def update(image: Image.Image) -> None:
    with open(_FB_PATH, "wb") as fb:
        fb.write(_encode(image))
