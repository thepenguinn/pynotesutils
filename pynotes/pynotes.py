import socket
import os

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
    server: socket.socket | None = None

    def __init__ (self, port: int | None = None, command: str | None = None, backlog: int = 4) -> None:

        if ViewServer.command is None:
            # if command is None then this is the first instance of this class
            # therefore we are setting the port, command and starting the server
            super().__init__(port = port, backlog = backlog)
            ViewServer.command = command or "termux-share"
            ViewServer.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((socket.gethostname(), self.port))
            self.server.listen(self.backlog)

        return

# client, adder = server.accept()
