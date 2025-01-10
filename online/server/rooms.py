import threading

from online.data.game_data import GameData, dump_game_sync_data, GAME_SYNC_ATTRS
from online.data.packets import send_packet, PacketTypes, Packet
from rules.game_flow import Player, PokerGame, GameEvent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from server_main import ClientHandler


class HandlerPlayer(Player):
    def __init__(self, game: "ServerGameRoom", client: "ClientHandler", name: str, chips: int):
        super().__init__(game, name, chips)
        self.client = client

    def receive_event(self, game_event: GameEvent):
        """
        When a `HandlerPlayer` receives a game event from the parent `ServerGameRoom`, it sends that event to its client
        by sending a game event packet through the socket.
        """

        # For some types of game events, send a game data packet.
        if game_event.code in GAME_SYNC_ATTRS:
            game_data: GameData = dump_game_sync_data(self.game, game_event.code)
            game_data.client_player_number = self.player_number

            if game_event.code == GameEvent.NEW_HAND:
                game_data.client_pocket_cards = self.player_hand.pocket_cards

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

        # List of non-participating players
        self.joining_queue: list[HandlerPlayer] = []
        self.spectators: list[HandlerPlayer] = []

    def join(self, client: "ClientHandler") -> HandlerPlayer or None:
        """
        Create a new `HandlerPlayer` for the client handler and append it to the joining queue.
        """
        if client.name in (x.name for x in self.players):
            raise ValueError("name already taken")

        new_handler_player = HandlerPlayer(self, client, client.name, self.starting_chips)

        if self.game_in_progress:
            # TODO the program should do more stuff
            self.joining_queue.append(new_handler_player)
            new_handler_player.receive_event(GameEvent(GameEvent.RESET_PLAYERS))

        else:
            self.players.append(new_handler_player)
            self.players[-1].player_number = len(self.players) - 1

            self.broadcast(GameEvent(GameEvent.RESET_PLAYERS))

        return new_handler_player

    def leave(self, client: "ClientHandler"):
        if self.game_in_progress:
            # TODO the program should do some other stuff
            client.current_player.leave_next_hand = True

        else:
            if client.current_player in self.players:
                self.players.remove(client.current_player)
            if client.current_player in self.spectators:
                self.spectators.remove(client.current_player)

            for i, player in enumerate(self.players):
                player.player_number = i

            self.broadcast(GameEvent(GameEvent.RESET_PLAYERS))

    def time_next_event(self, event):
        match event.code:
            case GameEvent.RESET_PLAYERS:
                pass

            case GameEvent.NEW_HAND:
                threading.Timer(2, self.hand.start_hand).start()

            case GameEvent.ROUND_FINISH:
                threading.Timer(1, self.hand.next_round).start()

            case GameEvent.NEW_ROUND:
                threading.Timer(2.25 + len(self.hand.community_cards) / 8, self.hand.start_new_round).start()

            case GameEvent.SKIP_ROUND:
                threading.Timer(2.25 + len(self.hand.community_cards) / 8, self.hand.next_round).start()

            case GameEvent.SHOWDOWN:
                threading.Timer(10, self.broadcast, (GameEvent(GameEvent.RESET_HAND),)).start()

            case GameEvent.RESET_HAND:
                reset_players = any(x.chips <= 0 or x.leave_next_hand for x in self.players)
                self.prepare_next_hand()

                if reset_players:
                    threading.Timer(2.5, self.broadcast, (GameEvent(GameEvent.RESET_PLAYERS),)).start()
                    threading.Timer(4.5, self.new_hand).start()

                else:
                    threading.Timer(3, self.new_hand).start()

    """
    Overridden methods
    """
    def on_event(self, event):
        self.time_next_event(event)

        """
        Broadcast the event to the non-participating players (clients who are in the room but aren't playing the game).
        """
        for player in self.spectators + self.joining_queue:
            player.receive_event(event)

    def prepare_next_hand(self, cycle_dealer=True):
        old_players = self.players.copy()
        super().prepare_next_hand(cycle_dealer)

        """
        Eliminated players who are still connected to the room are moved into the spectators list.
        """
        eliminated_players = [x for x in old_players if x not in self.players]
        self.spectators = [x for x in self.spectators + eliminated_players if x.client]

        """
        Add players from the joining queue
        """
        while self.joining_queue and len(self.players) < self.max_players:
            self.players.append(self.joining_queue.pop(0))
            self.players[-1].player_number = len(self.players) - 1
