import socket
import socketserver
import threading
import datetime

from online import packets

# HOST = socket.gethostbyname(socket.gethostname())
HOST = "localhost"
PORT = 32727

STARTUP_TEXT = "  ___  _ _ _              \n" \
               " / _ \\| | (_)            \n" \
               "/ /_\\ \\ | |_ _ __       \n" \
               "|  _  | | | | '_ \\       \n" \
               "| | | | | | | | | |       \n" \
               "\\_| |_/_|_|_|_| |_|    \n\n" \
               "Allin v0.5.0 Server       \n" \
               "Copyright (c) Patrick Kosasih 2023-2024\n"


def log(message):
    print("{:15}".format(datetime.datetime.now().strftime("%H:%M:%S")), end="")
    print("{:35}".format(threading.current_thread().name), end="")

    print(message)


class ClientHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server: "AllinServer"):
        super().__init__(request, client_address, server)
        self.server: AllinServer

    def handle(self):
        threading.current_thread().name = f"Client {self.client_address[0]}:{self.client_address[1]}"
        self.server: AllinServer
        self.server.clients.append(self)

        log("New connection established.")

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
            self.server.clients.remove(self)
            log("Connection closed.")

    def handle_packet(self, packet: packets.Packet):
        if type(packet) is packets.Message:
            packet: packets.Message
            log(f"Message received: {packet.message}")


class AllinServer(socketserver.ThreadingTCPServer):
    def __init__(self):
        super().__init__((HOST, PORT), ClientHandler)
        print(STARTUP_TEXT)

        self.clients: list[ClientHandler] = []

        threading.Thread(target=self.console, name="Server Console").start()

        threading.current_thread().name = "Server Listener"
        log(f"Server is now listening on port {PORT}.")
        self.serve_forever()

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
                    log("Server has been shut down.")
                    break

                case "count":
                    print(f"Current thread count: {threading.active_count()}")

                case "list":
                    print("\n".join(f"{i}. {client.client_address}" for i, client in enumerate(self.clients)))
                    print(f"There are currently {len(self.clients)} clients connected to this server:\n")

                case "broadcast":
                    for client in self.clients:
                        packets.send_packet(client.request, packets.Message(message=" ".join(command_args)))
                    print("Message broadcasted.")

                case "":
                    pass

                case _:
                    print("Invalid command.")
