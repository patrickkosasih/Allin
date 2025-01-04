"""
app/rules_interface/multiplayer.py

The multiplayer module is used to interface multiplayer games from the screen to the inputs to the client comms to the
server.
"""
from multiprocessing.connection import Client

from online.client.client_comms import ClientComms
from online.data.game_data import GameData
from online.data.packets import Packet, PacketTypes
from app.rules_interface.interface import InterfaceGame
from rules.game_flow import GameEvent, Player


class MultiplayerGame(InterfaceGame):
    def __init__(self):
        super().__init__()
        self.client_player = Player(self, "YOU", 1000)  # TODO change later

    def sync_game(self, game_data: GameData):
        # this will be our last jujutsu kaisen, sukuna
        if game_data.players:
            old_players_dict = {x.name: x for x in self.players}
            new_players_list = []

            for player_attr in game_data.players:
                if player_attr.name in old_players_dict:
                    # Existing player
                    player = old_players_dict[player_attr.name]
                    player.chips = player_attr.chips
                    new_players_list.append(player)

                else:
                    # New player
                    player = Player(self, player_attr.name, player_attr.chips)
                    new_players_list.append(player)

            self.players = new_players_list

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
