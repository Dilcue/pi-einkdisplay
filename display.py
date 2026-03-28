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


def update(image: Image.Image) -> None:
    # Convert 1-bit image to 32-bit RGBA that the repaper DRM framebuffer expects.
    # Invert before converting so black text on white renders correctly on the panel.
    from PIL import ImageOps
    rgba = ImageOps.invert(image.convert("L")).convert("RGBA")
    raw = rgba.tobytes()
    with open(_FB_PATH, "wb") as fb:
        fb.write(raw)
