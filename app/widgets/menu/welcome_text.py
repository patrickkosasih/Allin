import random

import pygame
from pygame import Vector2

from app.shared import FontSave
from app.tools import app_timer, app_async
from app.widgets.widget import Widget, WidgetComponent
from app.animations.interpolations import *


class WelcomeText(Widget):
    """
    A text with a satisfying character-by-character animation that shows up when the game is opened.
    """

    def __init__(self, parent, *rect_args, font: pygame.font.Font = None,
                 text_str="Welcome to Allin!", color=(255, 255, 255),
                 anim_duration=2.0, anim_interval=0.1):
        super().__init__(parent, *rect_args)

        self.font = font if font else pygame.font.Font("assets/fonts/Raleway Thin.ttf", int(0.15 * self.rect.h))
        # self.font = font if font else FontSave.get_font(7.5, "%")
        self.text_str = text_str
        self.color = color

        self.characters: list[WidgetComponent] = []

        self.init_characters()
        app_async.Coroutine(self.animate_characters(anim_duration, anim_interval))

    def init_characters(self):
        # X position of the next character in the list.
        next_x = 0

        # How far should every character be shifted to center the text.
        text_w, text_h = self.font.size(self.text_str)
        shift_x = self.rect.w / 2 - text_w / 2
        shift_y = self.rect.h / 2 - text_h / 2

        for c, (minx, maxx, miny, maxy, advance) in zip(self.text_str, self.font.metrics(self.text_str)):
            """
            The Pygame `Font.metrics` method provides each character's measurements on a given string were it to be
            rendered using said font. It returns a list of tuples where each tuple contains 5 integer values: minx,
            maxx, miny, maxy, and advance.
            
            The only used value in this scenario is the `advance` value, where it represents the distance (in pixels)
            between the leftmost point of a character to the leftmost point of the character after it.
            """

            char_component = WidgetComponent(self, next_x + shift_x, shift_y, 0, 0)

            char_component.image = self.font.render(c, True, self.color)
            char_component.image.set_alpha(0)

            self.characters.append(char_component)
            next_x += advance

    def animate_characters(self, duration=2.0, interval=0.1):
        for c in self.characters:
            start_pos = Vector2(c.get_pos()) + Vector2(0.25 * self.rect.h, 0).rotate(random.uniform(-180, 180))

            c.fade_anim(duration, 255)
            c.move_anim(duration, c.get_pos(), start_pos=start_pos, interpolation=lambda x: ease_out(x, 3.0))
            yield interval
