"""
online/client/client_comms.py

The client comms module is the bridge for the game client to the server.
"""

import socket
import threading
import time
from typing import Generator, Optional

from typing import TYPE_CHECKING

from online.data.game_sync import GameSyncEvent
from rules.game_flow import GameEvent

if TYPE_CHECKING:
    from app.app_main import App
    from app.rules_interface.multiplayer import MultiplayerGame

# import pygame.event

from app.tools import app_async
from online.data import packets
from online.data.packets import Packet, PacketTypes

HOST = "localhost"  # Temporary server address config
PORT = 32727


def log(*message):
    print("[Comms Log]", *message)


# Static class
class ClientComms:
    client_socket: socket.socket = None

    online: bool = False
    connecting: bool = False

    request_queue: list[int] = []
    last_response: str = ""

    app: Optional["App"] = None
    current_game: "MultiplayerGame" = None
    game_event_queue: list[GameEvent or GameSyncEvent] = []

    should_update_name = True

    @staticmethod
    def connect(threaded=True):
        if ClientComms.online or ClientComms.connecting:
            return
        elif threaded:
            threading.Thread(target=ClientComms.connect, args=(False,), daemon=True).start()
            return

        log("Connecting...")
        ClientComms.connecting = True

        try:
            ClientComms.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ClientComms.client_socket.connect((HOST, PORT))

            ClientComms.online = True
            ClientComms.request_queue = []
            log(f"Connected to {HOST}")
            threading.Thread(target=ClientComms.receive, daemon=True).start()

        except (socket.error, OSError) as e:
            log(f"Failed to connect to {HOST}: {e}")

        finally:
            ClientComms.connecting = False

    @staticmethod
    def disconnect():
        if ClientComms.client_socket:
            ClientComms.client_socket.shutdown(socket.SHUT_RDWR)

        if ClientComms.current_game:
            ClientComms.app.leave_game()

        ClientComms.client_socket = None
        ClientComms.online = False
        ClientComms.should_update_name = True

        log("Disconnected.")

    @staticmethod
    def receive():
        try:
            while True:
                packet: packets.Packet = packets.receive_packet(ClientComms.client_socket)

                if not packet:
                    break

                match packet.packet_type:
                    case PacketTypes.BASIC_RESPONSE:
                        ClientComms.last_response = packet.content

                    case PacketTypes.GAME_EVENT:
                        log("Received game event:", packet.content)
                        ClientComms.game_event_queue.append(packet.content)

        except (ConnectionResetError, TimeoutError, OSError, EOFError) as e:
            log(f"Disconnected from server: {e}")

        finally:
            ClientComms.disconnect()

    @staticmethod
    def send_packet(packet: packets.Packet):
        if not ClientComms.online:
            return

        try:
            packets.send_packet(ClientComms.client_socket, packet)

        except (ConnectionResetError, TimeoutError) as e:
            log(f"Failed to send packet: {e}")
            ClientComms.disconnect()

    @staticmethod
    def send_request(command: str) -> Generator[app_async.ThreadWaiter or float, str, str]:
        """
        Send a basic request packet to the server and wait for the response.

        :param command:
        :return:
        """
        if not ClientComms.online:
            return ""

        check_delay = 0.05

        req_time = time.time_ns()
        ClientComms.request_queue.append(req_time)

        # Wait until it's the call's turn on the request queue.
        while ClientComms.request_queue[0] != req_time:
            yield check_delay

        # Send request
        send_task = app_async.ThreadWaiter(ClientComms.send_packet, (Packet(PacketTypes.BASIC_REQUEST, content=command),))
        yield send_task

        # Wait for response
        wait_time = 0

        while not ClientComms.last_response:
            wait_time += check_delay
            yield check_delay

            if wait_time >= 3:
                ClientComms.request_queue.pop(0)
                ClientComms.last_response = ""
                log(f"Request: {command} -> Timed out: the server did not send back a basic response.")
                return "ERROR timeout"

        response = ClientComms.last_response
        log(f"Request: {command} -> Response: {response}")

        # Pop the queue and reset the last response
        ClientComms.request_queue.pop(0)
        ClientComms.last_response = ""

        return response

    @staticmethod
    def is_in_multiplayer() -> bool:
        return ClientComms.current_game is not None
