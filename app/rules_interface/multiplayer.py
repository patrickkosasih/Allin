"""
app/rules_interface/multiplayer.py

The multiplayer module is used to interface multiplayer games from the screen to the inputs to the client comms to the
server.
"""

from online.client.client_comms import ClientComms
from online.data.packets import Packet, PacketTypes
from app.rules_interface.interface import InterfaceGame
from rules.game_flow import GameEvent


class MultiplayerGame(InterfaceGame):
    def __init__(self):
        super().__init__()

    def sync_game(self):
        # this will be our last jujutsu kaisen, sukuna
        ...

    def on_event(self, event):
        self.event_receiver(event)

    def action(self, action_type, new_amount=0):
        ClientComms.send_packet(Packet(PacketTypes.GAME_ACTION, content=(action_type, new_amount)))

    def broadcast(self, broadcast: GameEvent) -> None:
        pass
