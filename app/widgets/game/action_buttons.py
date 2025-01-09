import pygame
import typing
from abc import ABC, abstractmethod

from app.animations.move import MoveAnimation
from app.widgets.basic.button import Button
from app.animations.interpolations import *
from app.shared import *
from rules.game_flow import *
if typing.TYPE_CHECKING:
    from app.scenes.game_scene import GameScene


COLORS = {
    "fold": (184, 51, 51),
    "call": (24, 142, 163),
    "raise": (168, 149, 24)
}


class ActionButton(Button, ABC):
    """
    `ActionButton` is the parent abstract class for all the action buttons.
    """

    def __init__(self, parent: "GameScene", *rect_args, **kwargs):
        super().__init__(parent, *rect_args, command=self.command, **kwargs)

        self.game_scene = self.parent

        self.original_pos = Vector2(self.rect.center)
        self.hidden_pos = self.original_pos + Vector2(1.2 * self.rect.width, 0)

    def set_shown(self, shown: bool, duration=0.5):
        new_pos = self.original_pos if shown else self.hidden_pos
        self.move_anim(duration, new_pos, "px", "tl", "ctr", interpolation=ease_out if shown else ease_in)

    @abstractmethod
    def update_bet_amount(self, new_bet_amount: int):
        pass

    @abstractmethod
    def command(self):
        pass

    @property
    def player(self):
        self.parent: "GameScene"
        return self.parent.game.client_player


class SideTextedButton(Button):
    """
    The side texted button is a button with an additional "side text" on the right hand side of the button. This side
    text is used to display the amount of chips the player needs to spend to make a call or raise. The side text also
    has a special rainbow effect when an action results in all in.

    There are currently two subclasses of SideTextedButton:
    1. CallButton: also a subclass of ActionButton
    2. BetConfirmButton
    """

    def __init__(self, parent, *rect_args, **kwargs):
        super().__init__(parent, *rect_args,  **kwargs)

        self.side_text = pygame.sprite.Sprite(self.component_group)
        self.set_side_text_int(0)

        self.all_in = False
        self.rainbow_fac = 0

    def set_side_text_int(self, amount: int):
        side_text_str = f"-${amount:,}" if amount > 0 else ""
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


class FoldButton(ActionButton):
    def __init__(self, parent, *rect_args):
        super().__init__(parent, *rect_args, color=COLORS["fold"], text_str="Fold",
                         icon=load_image("assets/sprites/action icons/fold.png"), icon_size=0.8)

    def command(self):
        self.game_scene.game.action(Actions.FOLD)

    def update_bet_amount(self, new_bet_amount: int):
        pass


class CallButton(ActionButton, SideTextedButton):
    def __init__(self, parent, *rect_args):
        super().__init__(parent, *rect_args, color=COLORS["call"], text_str="Call")

    def command(self):
        self.game_scene.game.action(Actions.CALL)

    def update_bet_amount(self, new_bet_amount: int):
        amount_to_pay = new_bet_amount - self.player.player_hand.current_round_spent

        if amount_to_pay > 0:
            self.set_text("Call")
            self.set_icon(load_image("assets/sprites/action icons/call.png"), 0.9)
        else:
            self.set_text("Check")
            self.set_icon(load_image("assets/sprites/action icons/check.png"), 0.8)

        self.all_in = amount_to_pay >= self.player.chips

        self.set_side_text_int(amount_to_pay)


class RaiseButton(ActionButton):
    """
    The bet/raise button toggles the bet prompt to be shown or hidden.
    """

    def __init__(self, parent: "GameScene", *rect_args):
        super().__init__(parent, *rect_args, color=COLORS["raise"], text_str="Raise")

        # Fields for toggling between show/hide bet prompt
        self.original_icon = None
        self.original_text = ""

    def command(self):
        self.game_scene.show_bet_prompt(not self.game_scene.bet_prompt.shown)

        if self.game_scene.bet_prompt.shown:
            self.set_text("Cancel")
            self.set_icon(load_image("assets/sprites/action icons/cancel.png"), 0.9)
            self.set_color((100, 100, 100))
        else:
            self.set_text(self.original_text)
            self.set_icon(self.original_icon, 0.9)
            self.set_color(COLORS["raise"])

    def update_bet_amount(self, new_bet_amount: int):
        if new_bet_amount > 0:
            self.original_text = "Raise"
            self.original_icon = load_image("assets/sprites/action icons/raise.png")
        else:
            self.original_text = "Bet"
            self.original_icon = load_image("assets/sprites/action icons/bet.png")

        self.set_text(self.original_text)
        self.set_icon(self.original_icon, 0.9)
        self.set_color(COLORS["raise"])
