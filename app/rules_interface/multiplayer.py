"""
app/rules_interface/multiplayer.py

The multiplayer module is used to interface multiplayer games from the screen to the inputs to the client comms to the
server.
"""

from online.client.client_comms import ClientComms
from online.packets import Packet, PacketTypes
from app.rules_interface.interface import InterfaceGame


class MultiplayerGame(InterfaceGame):
    def __init__(self):
        super().__init__()

    def action(self, action_type, new_amount=0):
        ClientComms.send_packet(Packet(PacketTypes.GAME_ACTION, content=(action_type, new_amount)))

    def sync_game(self):
        # this will be our last jujutsu kaisen, sukuna
        ...
