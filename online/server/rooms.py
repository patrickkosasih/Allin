from rules.game_flow import Player, PokerGame, GameEvent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from server_main import ClientHandler, AllinServer


class HandlerPlayer(Player):
    def __init__(self, game: "ServerGameRoom", client: "ClientHandler", name: str, chips: int):
        super().__init__(game, name, chips)
        self.client = client

    def receive_event(self, game_event: GameEvent):
        # Send the event to the client
        ...


class ServerGameRoom(PokerGame):
    def __init__(self):
        super().__init__()

        # Customizable room data stuff
        self.max_players = 10
        self.starting_chips = 1000
        self.sb_amount = 25  # Attribute of PokerGame

        # Other stuff
        self.joining_queue: list[HandlerPlayer] = []

    def join(self, client: "ClientHandler") -> HandlerPlayer or None:
        """
        Create a new `HandlerPlayer` for the client handler and append it to the joining queue.
        """
        handler_player = HandlerPlayer(self, client, client.name, self.starting_chips)

        if self.game_in_progress:
            self.joining_queue.append(handler_player)
        else:
            self.players.append(handler_player)

        return handler_player

    def leave(self, client: "ClientHandler"):
        ...

    def prepare_next_hand(self, cycle_dealer=True):
        super().prepare_next_hand(cycle_dealer)

        """
        Add players from the joining queue
        """
        while self.joining_queue and len(self.players) < self.max_players:
            self.players.append(self.joining_queue.pop(0))
            self.players[-1].player_number = len(self.players) - 1
