import socket
import socketserver
import threading
import datetime
from typing import Any, Optional

from online.data import packets
from online.data.packets import PacketTypes, Packet, send_packet
from online.server.rooms import HandlerPlayer, ServerGameRoom

# Server address binding stuff
# HOST = socket.gethostbyname(socket.gethostname())
HOST = "localhost"
PORT = 32727

# Fancy stuffs
POWER_SYMBOL = "⏻"
CONNECT_SYMBOL = "ᯤ"
STARTUP_TEXT = "  ___  _ _ _              \n" \
               " / _ \\| | (_)            \n" \
               "/ /_\\ \\ | |_ _ __       \n" \
               "|  _  | | | | '_ \\       \n" \
               "| | | | | | | | | |       \n" \
               "\\_| |_/_|_|_|_| |_|    \n\n" \
               "Allin v0.5.0 Server       \n" \
               "Copyright (c) Patrick Kosasih 2023-2025\n"


def log(*message, symbol="i"):
    print("{:15}".format(datetime.datetime.now().strftime("%H:%M:%S")), end="")
    print("{:35}".format(threading.current_thread().name), end="")
    print(f"[{symbol}] ", end="")
    print(*message)


class ClientHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server: "AllinServer"):
        super().__init__(request, client_address, server)
        self.server: AllinServer

        self.name: str = ""
        self.current_room: Optional[ServerGameRoom] = None
        self.current_player: Optional[HandlerPlayer] = None

    def handle(self):
        threading.current_thread().name = f"Client {self.client_address[0]}:{self.client_address[1]}"
        self.server: AllinServer
        self.server.clients.append(self)

        self.name = f"Port {self.client_address[1]}"  # TODO Make this customizable later.
        self.current_room = None
        self.current_player = None

        log("New connection established.", symbol=CONNECT_SYMBOL)

        try:
            while True:
                packet = packets.receive_packet(self.request)

                if packet:
                    self.handle_packet(packet)
                else:
                    break

        except (OSError, EOFError) as e:
            pass
            # log(f"Client has disconnected with the exception {type(e).__name__}: {e}.")

        finally:
            self.leave_room()
            self.server.clients.remove(self)
            log("Connection closed.", symbol=CONNECT_SYMBOL)

    def handle_packet(self, packet: packets.Packet):
        match packet.packet_type:
            case PacketTypes.BASIC_REQUEST:
                self.handle_basic_request(packet)

            case PacketTypes.GAME_ACTION:
                ...

    def handle_basic_request(self, packet: packets.Packet):
        if type(packet.content) is not str:
            self.send_basic_response("ERROR contents of a basic request packet must be str")
            return

        log(f"Received basic request: {packet.content}")

        try:
            sep = packet.content.index(" ")
            req_type, req_args = packet.content[:sep], packet.content[sep + 1:]
        except ValueError:  # No space in command
            req_type, req_args = packet.content, ""

        match req_type:
            case "echo":
                self.send_basic_response(req_args)

            case "public":
                self.send_basic_response("here are some public rooms bruv: <list of rooms>")

            case "code":
                self.send_basic_response(f"here is some info regarding the room with code {req_args}: <some room info>")

            case "join":
                # self.send_basic_response(f"you joined room {req_args}")
                try:
                    self.join_room(req_args)
                    self.send_basic_response("SUCCESS")

                except (ValueError, KeyError) as e:
                    log(f"Failed to join room: {e}", symbol="X")
                    self.send_basic_response(f"ERROR failed to join room: {e}")

            case "leave":
                self.leave_room()
                self.send_basic_response("SUCCESS")

            case _:
                self.send_basic_response("ERROR invalid request command")

    def send_basic_response(self, content: Any):
        send_packet(self.request, Packet(PacketTypes.BASIC_RESPONSE, content=content))

    def join_room(self, room_code: str):
        self.server: AllinServer

        if len(room_code) != 4 and not room_code.isupper():
            raise ValueError(f"invalid room code: {room_code}")
        elif room_code not in self.server.rooms:
            raise KeyError(f"room does not exist: {room_code}")
        elif self.current_room:
            raise ValueError("client is already in another room")

        room = self.server.rooms[room_code]
        player = room.join(self)

        if player:
            self.current_room = room
            self.current_player = player
            log(f"Player has joined room {room_code}. {len(room.players)} player(s) in room.")

    def leave_room(self):
        if not self.current_room:
            return

        log(f"Player has left the room. {len(self.current_room.players) - 1} player(s) remaining.")

        self.current_room.leave(self)
        self.current_room = None
        self.current_player = None


class AllinServer(socketserver.ThreadingTCPServer):
    def __init__(self):
        super().__init__((HOST, PORT), ClientHandler)
        print(STARTUP_TEXT)

        self.clients: list[ClientHandler] = []
        self.rooms: dict[str, ServerGameRoom] = {}

        threading.Thread(target=self.console, name="Server Console").start()

        threading.current_thread().name = "Server Listener"
        log(f"Server is now listening on port {PORT}.", symbol=POWER_SYMBOL)
        self.serve_forever()
        log("Server has been shut down.", symbol=POWER_SYMBOL)

    def console(self):
        while True:
            command = input()
            command_args = []

            if len(split_input := command.split()) > 1:
                command, *command_args = split_input

            match command:
                case "shutdown":
                    log("Shutting down server...")
                    for client in self.clients:
                        client.request.shutdown(socket.SHUT_RDWR)
                    self.shutdown()
                    break

                case "count":
                    log(f"Current thread count: {threading.active_count()}")

                case "list":
                    invalid_list_cmd = False

                    if not command_args:
                        invalid_list_cmd = True

                    elif command_args[0] == "clients":
                        log(f"There are currently {len(self.clients)} clients connected to this server:\n")
                        print("\n".join(f"{i}. {client.client_address}" for i, client in enumerate(self.clients)))

                    elif command_args[0] == "rooms":
                        log(f"There are currently {len(self.rooms)} active rooms:\n")
                        print("\n".join(f"Room {code} | {len(room.players)} players: "
                                        f"{', '.join(x.name for x in room.players)}"
                                        for code, room in self.rooms.items()))

                    else:
                        invalid_list_cmd = True

                    if invalid_list_cmd:
                        log("Invalid argument for the list command. Correct usage: \"list <clients|rooms>\"", symbol="X")

                case "create":
                    # TODO Temporary testing stuff.
                    self.rooms["AAAA"] = ServerGameRoom()
                    self.rooms["AAAB"] = ServerGameRoom()
                    log("Created rooms AAAA and AAAB.")

                case "start":
                    self.rooms["AAAA"].start_game()
                    log("Game started on room AAAA.")

                case "":
                    pass

                case _:
                    log("Invalid command.", symbol="X")

