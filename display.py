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
    """Trigger a global refresh by writing a full-black frame.

    The repaper driver fires its global waveform (black flash → white flash)
    when it receives an all-black frame, which eliminates ghosting. The
    subsequent page render provides the white-to-content transition.
    """
    black = Image.new("1", _SIZE, 0)  # 0 = black
    with open(_FB_PATH, "wb") as fb:
        fb.write(_encode(black))


def update(image: Image.Image) -> None:
    with open(_FB_PATH, "wb") as fb:
        fb.write(_encode(image))
