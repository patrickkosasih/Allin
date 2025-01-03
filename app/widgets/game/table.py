import random

from math import sin, cos, pi

from app.shared import load_image
from app.widgets.widget import Widget
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.scenes.game_scene import GameScene


class Table(Widget):
    def __init__(self, parent: "GameScene", *rect_args):
        super().__init__(parent, *rect_args)

        self._image = load_image("assets/sprites/misc/table.png", self.rect.size)

    def get_player_rotation(self, i: int, n_players: int = 0) -> float:
        """
        Returns the player rotation for the given player index and number of players.

        A player rotation defines the position of a player display in the table. The returned player rotation is usually
        converted into a (x, y) position using the `Table.get_edge_coords` method.

        :param i: The index of the player.
        :param n_players: Override the total number of players. If set to 0 or lower, then the number of players is
                          get from the game object of the game scene by default.
        :return: The player rotation in degrees.
        """

        self.parent: "GameScene"
        n_players = len(self.parent.game.players) if n_players <= 0 else n_players
        client_player_number = self.parent.game.client_player.player_number

        if client_player_number == -2:
            client_player_number = 0

        return (i - client_player_number) * (360 / n_players) + 90

    def get_edge_pos(self, degrees: float,
                        scale: tuple[float, float] = (1.0, 1.0),
                        randomize_fac: float = 0.0) -> tuple[float, float]:

        degrees += random.uniform(-randomize_fac, randomize_fac)
        rad = degrees / 180 * pi

        x, y = self.rect.center
        rx, ry = scale[0] * self.rect.width / 2, scale[1] * self.rect.height / 2

        return x + rx * cos(rad), y + ry * sin(rad)

    def get_player_pos(self, player_number: int,
                        scale: tuple[float, float] = (1.0, 1.0),
                        randomize_fac: float = 0.0) -> tuple[float, float]:

        """
        Get the position for a player based on its player number. Every player is positioned to form an ellipse around
        the ellipse-shaped table.

        :param player_number: The player number/index.
        :param scale: The scale of the ellipse around the table.
        :param randomize_fac: How many degrees maximum to shift from the original player rotation.
        :return: The position tuple (x, y).
        """

        return self.get_edge_pos(self.get_player_rotation(player_number), scale, randomize_fac)
