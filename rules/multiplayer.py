from online.client.client_comms import ClientComms
from online.packets import Packet, PacketTypes
from rules.interface import ClientPlayer, InterfaceGame


class MultiplayerGame(InterfaceGame):
    def __init__(self):
        super().__init__()

    def action(self, action_type, new_amount=0):
        ClientComms.send_packet(Packet(PacketTypes.GAME_ACTION, content=(action_type, new_amount)))

    def sync_game(self):
        # this will be our last jujutsu kaisen, sukuna
        ...
