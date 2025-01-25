import pygame
from pygame.math import Vector2
from typing import TYPE_CHECKING

from app.shared import Layer, h_percent_to_px, load_image
from app.widgets.widget import Widget

if TYPE_CHECKING:
    from app.widgets.game.player_display import PlayerDisplay

SPRITE_PATHS = {
    "D": "assets/sprites/dealer buttons/d.png",
    "SB": "assets/sprites/dealer buttons/sb.png",
    "BB": "assets/sprites/dealer buttons/bb.png"
}

LAYERS = {
    "D": Layer.DEALER_BUTTON,
    "SB": Layer.SB_BUTTON,
    "BB": Layer.BB_BUTTON
}


class DealerButton(Widget):
    def __init__(self, parent, x, y, button_type="D", d_percent=3.5, shown=False):
        """
        Parameters:

        :param x: Initial x position. Units are in pixels, anchor is on the top left, and pivot is the center.
        :param y: Initial y position. Units are in pixels, anchor is on the top left, and pivot is the center.
        :param button_type: The type of the button, or the letter(s) that are shown on the button.
                            Possible types: "D", "SB", "BB". Case-insensitive.
        :param d_percent: The diameter of the button. Units are in percent of the screen's height.
        """

        d_px = h_percent_to_px(d_percent)

        super().__init__(parent, x, y, d_px, d_px, "px", "tl", "ctr")

        button_type = button_type.upper()
        if button_type not in SPRITE_PATHS:
            raise ValueError(f"invalid button type: {button_type}")

        self._image = load_image(SPRITE_PATHS[button_type], self.rect.size)
        self.layer = LAYERS[button_type]

        self._shown = shown
        if not shown:
            self.image.set_alpha(0)

    def set_shown(self, shown: bool, duration=0.25):
        if shown != self._shown:
            self.fade_anim(duration, 255 if shown else 0)

        self._shown = shown

    def move_to_player(self, duration: float,
                       player: "PlayerDisplay",
                       start_pos_button: "DealerButton" or None = None,
                       **move_kwargs):

        """
        Unhides and moves the dealer/blinds button to a player.

        If the dealer button is shown, it simply moves from its current position to the new one.

        On the contrary, if the dealer button is hidden, it gets shown and either starts moving from an existing
        dealer/blinds (`start_pos_button`), or starts moving from offscreen (if `start_pos_button` is set to None).
        """

        end_pos = Vector2(player.rect_after_move.topleft) + player.head_base.rect.midright
        start_pos = None

        if not self._shown:
            if start_pos_button:
                start_pos = start_pos_button.get_pos("px", "tl", "ctr")
            else:
                screen_center = self.parent.rect.center
                start_pos = screen_center + 3 * (Vector2(end_pos) - screen_center)  # Offscreen

            self.set_pos(*start_pos, "px", "tl", "ctr")
            self.set_shown(True, duration=0)

        self.move_anim(duration, end_pos, "px", "tl", "ctr", start_pos=start_pos, **move_kwargs)


