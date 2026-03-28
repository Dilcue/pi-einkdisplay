from PIL import Image, ImageDraw
from papirus import Papirus

_disp = None


def init() -> Papirus:
    global _disp
    _disp = Papirus()
    return _disp


def get() -> Papirus:
    if _disp is None:
        raise RuntimeError("Display not initialised — call display.init() first")
    return _disp


def new_image() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    disp = get()
    image = Image.new("1", disp.size, 1)  # 1 = white
    draw = ImageDraw.Draw(image)
    return image, draw


def update(image: Image.Image) -> None:
    disp = get()
    disp.display(image)
    disp.update()
