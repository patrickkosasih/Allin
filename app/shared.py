"""
app/shared.py

A module that contains various shared functions used throughout the program.
"""


# When another module imports this module by `from app.shared import *`, all the imports below are imported as well.

import os

import pygame
from pygame.math import Vector2
from pygame.event import Event
from typing import Callable, Optional, Iterable, Generator, Any
import time
import sys

from app.tools.colors import hsv_factor, rand_color
from app.tools.draw import draw_rounded_rect


"""
Shared constants
"""
VERSION_ID = 5000
VERSION_TEXT = "Allin v0.5.0"
if not getattr(sys, "frozen", False):
    VERSION_TEXT += " (Uncompiled/Development Build)"

SAVE_FOLDER_PATH = os.path.join(os.getenv("localappdata"), "Allin") if os.getenv("localappdata") else "./save"
if not os.path.isdir(SAVE_FOLDER_PATH):
    os.mkdir(SAVE_FOLDER_PATH)


"""
Image loading-related tools
"""
class FontSave:
    """
    The `FontSave` class makes creating font objects much easier by having a global font object that is shared
    throughout the program.
    """

    DEFAULT_FONT_PATH = "assets/fonts/coolvetica condensed rg.ttf"

    font_dict = {}

    @staticmethod
    def get_font(size, unit="%"):
        """
        Returns a shared font object.

        :param size: The size of the font.
        :param unit: The unit for size. Possible units: "%" - % height (default)
                                                        "px" - Pixels
        """
        if unit == "px":
            size = size / pygame.display.get_window_size()[1] * 100

        return FontSave.font_dict.setdefault(
            size,
            pygame.font.Font(FontSave.DEFAULT_FONT_PATH, int(h_percent_to_px(size)))
        )

    @staticmethod
    def reset():
        FontSave.font_dict = {}


def load_image(path: str,
               size: None or tuple = None,
               convert: int = 1) -> pygame.Surface:
    """
    Load an image file into a pygame.Surface object, and convert it to the correct pixel format using `convert_alpha`.
    A much simpler way of writing `pygame.image.load(path).convert_alpha()`.

    :param path: Path to the image file.

    :param size: A tuple representing the width and height for the image to be resized to.
                 If set to None then the image is not resized.
                 If either the width or height of the size is set to 0, then the size would be based on the other
                 non-zero value while preserving the aspect ratio of the original image.

    :param convert: 0 - Image isn't converted
                    1 - Convert the image using `convert_alpha`
                    2 - Convert the image using `convert`

    :return: The loaded and converted image.
    """
    image = pygame.image.load(path)

    if size:
        if len(size) != 2 or (size[0] <= 0 and size[1] <= 0):
            raise ValueError(f"invalid size: {size}")

        aspect_ratio = image.get_width() / image.get_height()  # From unscaled image.
        w, h = size

        if w <= 0:
            w = int(h * aspect_ratio)
        elif h <= 0:
            h = int(w / aspect_ratio)

        image = pygame.transform.smoothscale(image, (w, h))

    if convert == 1:
        image = image.convert_alpha()
    elif convert == 2:
        image = image.convert()

    return image


"""
Universal layer order constants
"""
class Layer:
    BACKGROUND = -1
    DEFAULT = 0

    TABLE = 1
    TABLE_TEXT = 2

    CARD = 3
    WINNER_CROWN = 4
    PLAYER = 5

    BB_BUTTON = 6
    SB_BUTTON = 7
    DEALER_BUTTON = 8

    SIDE_MENU = 9


"""
Legacy % to px conversion functions
"""
def w_percent_to_px(x: float) -> float:
    return 0.01 * x * pygame.display.get_window_size()[0]


def h_percent_to_px(y: float) -> float:
    return 0.01 * y * pygame.display.get_window_size()[1]


def percent_to_px(x: float, y: float) -> tuple[float, float]:
    return w_percent_to_px(x), h_percent_to_px(y)


"""
Other useful functions
"""
def elementwise_mult(a: Iterable, b: Iterable) -> Generator:
    return (x * y for x, y in zip(a, b))


def func_timer(func):
    """
    A decorator function that measures the time taken to run a function
    """
    def wrapper(*args, **kwargs):
        time_before = time.perf_counter()
        ret = func(*args, **kwargs)  # Call function
        time_taken = time.perf_counter() - time_before

        print(f"{func.__name__} took {time_taken} seconds to run")
        return ret

    return wrapper
