from online.data.game_data import GameData, generate_game_data
from online.data.packets import send_packet, PacketTypes, Packet
from rules.basic import generate_deck
from rules.game_flow import Player, PokerGame, GameEvent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from server_main import ClientHandler


class HandlerPlayer(Player):
    def __init__(self, game: "ServerGameRoom", client: "ClientHandler", name: str, chips: int):
        super().__init__(game, name, chips)
        self.client = client

    def receive_event(self, game_event: GameEvent):
        # TODO Also send the game data according to the type of the game event.
        if game_event.code in (GameEvent.RESET_PLAYERS, GameEvent.NEW_HAND, GameEvent.ROUND_FINISH, GameEvent.SHOWDOWN):
            game_data = generate_game_data(self.game, game_event)
            send_packet(self.client.request, Packet(PacketTypes.GAME_DATA, game_data))

        # Forward the game event to the client by sending a game event packet.
        send_packet(self.client.request, Packet(PacketTypes.GAME_EVENT, game_event))


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
        if client.name in (x.name for x in self.players):
            raise ValueError("name already taken")

        handler_player = HandlerPlayer(self, client, client.name, self.starting_chips)

        if self.game_in_progress:
            self.joining_queue.append(handler_player)
        else:
            # TODO the program should do more stuff
            self.players.append(handler_player)
            self.broadcast(GameEvent(GameEvent.RESET_PLAYERS))

        return handler_player

    def leave(self, client: "ClientHandler"):
        if self.game_in_progress:
            client.current_player.leave_next_hand = True
        else:
            # TODO the program should do some other stuff
            self.players.remove(client.current_player)
            self.broadcast(GameEvent(GameEvent.RESET_PLAYERS))

    def prepare_next_hand(self, cycle_dealer=True):
        super().prepare_next_hand(cycle_dealer)

        """
        Add players from the joining queue
        """
        while self.joining_queue and len(self.players) < self.max_players:
            self.players.append(self.joining_queue.pop(0))
            self.players[-1].player_number = len(self.players) - 1
