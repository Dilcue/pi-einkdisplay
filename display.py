# display.py
import os
import pathlib
import time
from PIL import Image, ImageDraw, ImageFont

_WIDTH = 800
_HEIGHT = 480
_SIZE = (_WIDTH, _HEIGHT)
_PREVIEW_PATH = "/tmp/einkdisplay_preview.png"
_FONTS_DIR = pathlib.Path(__file__).parent / "fonts"

# Attempt to import the Adafruit hardware driver.
# Falls back to simulator if the library is absent (dev Mac) or EINK_SIMULATE=1.
_HW_AVAILABLE = False
try:
    import board
    import busio
    import digitalio
    from adafruit_epd.uc8179 import Adafruit_UC8179
    _HW_AVAILABLE = True
except ImportError:
    pass

_display = None  # set by init()


def _simulator_mode() -> bool:
    return os.environ.get("EINK_SIMULATE", "0") == "1" or not _HW_AVAILABLE


def init() -> None:
    global _display
    if _display is not None:
        return
    if _simulator_mode():
        return
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    ecs = digitalio.DigitalInOut(board.CE0)
    dc = digitalio.DigitalInOut(board.D22)
    rst = digitalio.DigitalInOut(board.D27)
    busy = digitalio.DigitalInOut(board.D17)
    _display = Adafruit_UC8179(
        800, 480, spi,
        cs_pin=ecs, dc_pin=dc, sramcs_pin=None,
        rst_pin=rst, busy_pin=busy,
        tri_color=True,
    )
    _display.rotation = 1


def new_image() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", _SIZE, (255, 255, 255))  # white background
    draw = ImageDraw.Draw(image)
    return image, draw


def update(image: Image.Image) -> None:
    if _display is None and not _simulator_mode():
        raise RuntimeError("display.init() must be called before display.update()")
    if _simulator_mode():
        image.save(_PREVIEW_PATH)
        return
    _display.image(image)
    _display.display()


def clear() -> None:
    """Write a full white frame (resets display to blank state)."""
    image = Image.new("RGB", _SIZE, (255, 255, 255))
    update(image)


def splash() -> None:
    """Show a startup splash screen for 1 second."""
    try:
        font = ImageFont.truetype(str(_FONTS_DIR / "nokiafc22.ttf"), 16)
    except OSError:
        font = ImageFont.load_default()
    image = Image.new("RGB", _SIZE, (0, 0, 0))  # black background
    draw = ImageDraw.Draw(image)
    draw.text((8, 8), "Loading Display...", font=font, fill=(255, 255, 255))
    update(image)
    time.sleep(1)
