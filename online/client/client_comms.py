"""
online/client/client_comms.py

The client comms module is the bridge for the game client to the server.
"""

import socket
import threading

import pygame.event

from online import packets


HOST = "localhost"  # Temporary server address config
PORT = 32727


# Static class
class ClientComms:
    client_socket: socket.socket = None

    online: bool = False
    connecting: bool = False

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
                elif type(packet) == packets.Message:
                    # pygame.event.post(pygame.event.Event(pygame.USEREVENT, packet=packet))
                    packet: packets.Message
                    print(f"Message from server: {packet.message}")

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
