import threading
import socket
import os

from typing import List

class ViewConnection():

    port: int | None = None
    backlog: int = 4

    def __init__ (self, port: int | None = None, backlog: int = 4) -> None:

        if ViewConnection.port is None:
            # if port is None, then this is the first instance of this class
            # therefore we are setting the port and backlog
            ViewConnection.port = port or 52886
            ViewConnection.backlog = backlog

        return

class ViewServer(ViewConnection):

    command: str | None = None
    server: socket.socket

    thread_list: List[threading.Thread] = []
    # command_lock will make sure that at a time only one
    # thread will be executing the command
    command_lock: threading.Lock

    def __init__ (self, port: int | None = None, command: str | None = None, backlog: int = 4) -> None:

        if ViewServer.command is None:
            # if command is None then this is the first instance of this class
            # therefore we are setting the port, command and starting the server
            super().__init__(port = port, backlog = backlog)
            ViewServer.command = command or "termux-share"
            ViewServer.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ViewServer.command_lock = threading.Lock()

            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((socket.gethostname(), self.port))
            self.server.listen(self.backlog)

        return

    def thread_handler (self, client: socket.socket) -> None:

        buf: bytearray
        size: int

        while True:

            buf = client.recv(4)
            if len(buf) < 4 and client.recv(1).decode() == "":
                print("Client got disconnected")
                print("Leaving the thread")
                break

            size = buf[0] | buf[1] << 8 | buf[2] << 16 | buf[3] << 24

            buf = client.recv(size)

            if len(buf) < size and client.recv(1).decode() == "":
                print("Client got disconnected")
                print("Leaving the thread")
                break

            print(buf.decode())

        return

    def start (self) -> None:

        connected_client: socket.socket
        thread: threading.Thread

        # TODO: Limit the number of threads, maybe to 20
        while True:
            # this will block
            print("Waiting for the client to connect")
            connected_client, _ = self.server.accept()
            print("client got connected")

            thread = threading.Thread(target = self.thread_handler, args = [connected_client])
            print("Starting the thread")
            thread.start()
            self.thread_list.append(thread)

        return

class ViewClient(ViewConnection):

    server: socket.socket

    def __init__ (self, port: int | None = None) -> None:

        if ViewClient.port is None:
            # if port is None then this is the first instance of this class
            # therefore we are setting the port and server
            super().__init__(port = port)
            ViewClient.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        return

    def connect (self) -> bool:

        try:
            self.server.connect((socket.gethostname(), self.port))
        except:
            print("Couldn't connect to server...\nExiting...")
        else:
            print("Connected to the server")
            return True

        return False

    def view (self, file: str, command: str | None = None) -> None:

        size: int
        buf: bytearray

        size = len(file)

        buf = bytearray([
            size & 0xff, (size >> 8) & 0xff, (size >> 16) & 0xff, (size >> 24) & 0xff
        ]) + file.encode()

        self.server.send(buf)

        return

# client, adder = server.accept()
