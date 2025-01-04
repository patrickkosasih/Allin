import pickle
from dataclasses import dataclass
import socket
import struct
from typing import Any


class PacketTypes:
    BASIC_REQUEST = 0
    BASIC_RESPONSE = 1

    GAME_ACTION = 2
    GAME_EVENT = 3
    GAME_DATA = 4


@dataclass
class Packet:
    packet_type: int
    content: Any = None


def send_packet(s: socket.socket, packet: Packet) -> None:
    """
    Send a packet through a socket.
    """
    packet_raw = pickle.dumps(packet)
    packet_len_raw = struct.pack("i", len(packet_raw))

    # print("Send packet", packet_raw)
    s.send(packet_len_raw)
    s.send(packet_raw)


def receive_packet(s: socket.socket) -> Packet or None:
    """
    Receive a packet from the given socket.
    """
    try:
        packet_len: int = struct.unpack("i", s.recv(4))[0]
        packet: Packet = pickle.loads(s.recv(packet_len))
        return packet

    except struct.error:
        return None
