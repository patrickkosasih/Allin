"""
online/client/client_comms.py

The client comms module is the bridge for the game client to the server.
"""

import socket
import threading
import time
from typing import Generator

import pygame.event

from app.tools import app_async
from online import packets
from online.packets import send_packet, Packet, PacketTypes

HOST = "localhost"  # Temporary server address config
PORT = 32727


class OnlineEvents:
    COMMS_STATUS = pygame.event.custom_type()

    ROOM_STATUS = pygame.event.custom_type()
    GAME_DATA = pygame.event.custom_type()
    GAME_EVENT = pygame.event.custom_type()


# Static class
class ClientComms:
    client_socket: socket.socket = None

    online: bool = False
    connecting: bool = False

    request_queue: list[int] = []
    last_response: str = ""

    @staticmethod
    def connect(threaded=True):
        if ClientComms.online or ClientComms.connecting:
            return
        elif threaded:
            threading.Thread(target=ClientComms.connect, args=(False,), daemon=True).start()
            return

        print("Connecting...")
        ClientComms.connecting = True

        try:
            ClientComms.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ClientComms.client_socket.connect((HOST, PORT))

            ClientComms.online = True
            print(f"Connected to {HOST}")
            threading.Thread(target=ClientComms.receive, daemon=True).start()

        except (socket.error, OSError) as e:
            print(f"Failed to connect to {HOST}: {e}")

        finally:
            ClientComms.connecting = False

    @staticmethod
    def disconnect():
        if ClientComms.client_socket:
            ClientComms.client_socket.shutdown(socket.SHUT_RDWR)

        ClientComms.client_socket = None
        ClientComms.online = False

        print("Disconnected.")

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

        except (ConnectionResetError, TimeoutError, OSError, EOFError):
            pass

        finally:
            ClientComms.disconnect()

    @staticmethod
    def send_packet(packet: packets.Packet):
        if not ClientComms.online:
            return

        try:
            packets.send_packet(ClientComms.client_socket, packet)

        except (ConnectionResetError, TimeoutError) as e:
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

        req_time = time.time_ns()
        ClientComms.request_queue.append(req_time)

        # Wait until it's the call's turn on the request queue.
        while ClientComms.request_queue[0] != req_time:
            yield 0.001

        # Send request
        send_task = app_async.ThreadWaiter(ClientComms.send_packet, (Packet(PacketTypes.BASIC_REQUEST, content=command),))
        yield send_task

        # Wait for response
        while not ClientComms.last_response:
            yield 0.001

        response = ClientComms.last_response

        # Pop the queue and reset the last response
        ClientComms.request_queue.pop(0)
        ClientComms.last_response = ""

        return response
