"""
app/rules_interface/multiplayer.py

The multiplayer module is used to interface multiplayer games from the screen to the inputs to the client comms to the
server.
"""
from multiprocessing.connection import Client

from online.client.client_comms import ClientComms
from online.data.game_data import GameData, load_attrs
from online.data.packets import Packet, PacketTypes
from app.rules_interface.interface import InterfaceGame
from rules.game_flow import GameEvent, Player


class MultiplayerGame(InterfaceGame):
    def __init__(self):
        super().__init__()
        self.client_player = Player(self, "Placeholder thingy", 1000)  # TODO change later

    def sync_game(self, game_data: GameData):
        """
        this will be our last jujutsu kaisen, sukuna
        """
        load_attrs(self, game_data.attr_dict, ["players", "hand"])

        if "players" in game_data.attr_dict:
            old_players_dict = {x.name: x for x in self.players}
            new_players_list = []

            for player_attr_dict in game_data.attr_dict["players"]:
                if player_attr_dict["name"] in old_players_dict:
                    # Existing player
                    player = old_players_dict[player_attr_dict["name"]]
                    player.chips = player_attr_dict["chips"]
                    new_players_list.append(player)

                else:
                    # New player
                    player = Player(self, player_attr_dict["name"], player_attr_dict["chips"])
                    new_players_list.append(player)

            self.players = new_players_list

            for i, player in enumerate(self.players):
                player.player_number = i

        if "hand" in game_data.attr_dict:
            if not self.game_in_progress:
                self.start_game()

            load_attrs(self.hand, game_data.attr_dict["hand"], ["players"])

        if game_data.client_player_number != -1:
            self.client_player = self.players[game_data.client_player_number]


    def on_event(self, event):
        self.event_receiver(event)

    def action(self, action_type, new_amount=0):
        ClientComms.send_packet(Packet(PacketTypes.GAME_ACTION, content=(action_type, new_amount)))

    def broadcast(self, broadcast: GameEvent) -> None:
        """
        `MultiplayerGame` objects do not broadcast anything. They only receive broadcasts from the server.
        """
        pass

    def update(self, dt):
        super().update(dt)

        if ClientComms.game_event_queue:
            event: GameEvent or GameData = ClientComms.game_event_queue.pop(0)

            if type(event) is GameEvent:
                self.on_event(event)
            elif type(event) is GameData:
                self.sync_game(event)
