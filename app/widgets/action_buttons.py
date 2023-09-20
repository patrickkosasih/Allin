import pygame.sprite
from pygame.math import Vector2
from abc import ABC, abstractmethod

import threading
import tkinter.simpledialog

from app.animations.move import MoveAnimation
from app.widgets.button import Button
from app.animations.interpolations import *
from app.shared import *
from rules.game_flow import *


COLORS = {
    "fold": (184, 51, 51),
    "call": (24, 142, 163),
    "raise": (168, 149, 24)
}


class ActionButton(Button, ABC):
    """
    `ActionButton` is the parent abstract class for all the action buttons.
    """

    def __init__(self, pos, dimensions, player: Player, **kwargs):
        super().__init__(pos, dimensions, command=self.on_click, **kwargs)

        self.original_pos = pos
        self.hidden_pos = pos + Vector2(1.2 * self.rect.width, 0)

        self.player = player

    def set_shown(self, shown: bool, duration=0.5):
        new_pos = self.original_pos if shown else self.hidden_pos
        new_rect = self.image.get_rect(center=new_pos)

        if duration > 0:
            animation = MoveAnimation(duration, self, None, new_pos, interpolation=ease_out if shown else ease_in)
            self.anim_group.add(animation)

        else:
            self.rect = new_rect

        self.global_rect = new_rect

    @abstractmethod
    def on_click(self):
        pass

    @abstractmethod
    def update_bet_amount(self, new_bet_amount: int):
        pass


class FoldButton(ActionButton):
    def __init__(self, pos, dimensions, player: Player):
        super().__init__(pos, dimensions, player, color=COLORS["fold"], text_str="Fold",
                         icon=pygame.image.load("assets/sprites/action icons/fold.png"), icon_size=0.8)

    def on_click(self):
        self.player.action(Actions.FOLD)

    def update_bet_amount(self, new_bet_amount: int):
        pass


class CallButton(ActionButton):
    def __init__(self, pos, dimensions, player: Player):
        super().__init__(pos, dimensions, player, color=COLORS["call"], text_str="Call")

        self.side_text = pygame.sprite.Sprite(self.component_group)
        self.set_side_text_money(0)

        self.all_in = False
        self.rainbow_fac = 0

    def on_click(self):
        self.player.action(Actions.CALL)

    def update_bet_amount(self, new_bet_amount: int):
        amount_to_pay = new_bet_amount - self.player.player_hand.bet_amount

        if amount_to_pay > 0:
            self.set_text("Call")
            self.set_icon(pygame.image.load("assets/sprites/action icons/call.png"), 0.9)
        else:
            self.set_text("Check")
            self.set_icon(pygame.image.load("assets/sprites/action icons/check.png"), 0.8)

        if amount_to_pay >= self.player.money:
            self.all_in = True

        self.set_side_text_money(amount_to_pay)

    def set_side_text_money(self, amount_to_pay):
        side_text_str = f"-${amount_to_pay:,}" if amount_to_pay > 0 else ""
        self.set_side_text(side_text_str, (247, 218, 136))

    def set_side_text(self, side_text_str: str, color: tuple):
        _, _, w, h = self.rect

        self.side_text.image = FontSave.get_font(3).render(side_text_str, True, color)
        self.side_text.rect = self.side_text.image.get_rect(midright=(w - h / 2, h / 2))

    def update_all_in(self, dt):
        _, _, w, h = self.rect

        color = hsv_factor((255, 64, 64), hf=self.rainbow_fac)
        self.set_side_text("ALL IN", color)

        self.rainbow_fac = (self.rainbow_fac + 2 * dt) % 1

    def update(self, dt):
        if self.all_in:
            self.update_all_in(dt)

        super().update(dt)


class RaiseButton(ActionButton):
    def __init__(self, pos, dimensions, player: Player, game_scene):
        super().__init__(pos, dimensions, player, color=COLORS["raise"], text_str="Raise")
        self.game_scene = game_scene

        # Fields for toggling between show/hide bet prompt
        self.original_icon = None
        self.original_text = ""

    def on_click(self):
        self.game_scene.show_bet_prompt(not self.game_scene.bet_prompt.shown)

        if self.game_scene.bet_prompt.shown:
            self.set_text("Cancel")
            self.set_icon(pygame.image.load("assets/sprites/action icons/cancel.png"), 0.9)
            self.set_color((100, 100, 100))
        else:
            self.set_text(self.original_text)
            self.set_icon(self.original_icon, 0.9)
            self.set_color(COLORS["raise"])

    def update_bet_amount(self, new_bet_amount: int):
        if new_bet_amount > 0:
            self.original_text = "Raise"
            self.original_icon = pygame.image.load("assets/sprites/action icons/raise.png")
        else:
            self.original_text = "Bet"
            self.original_icon = pygame.image.load("assets/sprites/action icons/bet.png")

        self.set_text(self.original_text)
        self.set_icon(self.original_icon, 0.9)
        self.set_color(COLORS["raise"])
