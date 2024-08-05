import threading
import pathlib
import socket
import os
import re

from typing import List

class Connection():

    port: int | None = None
    backlog: int

    def __init__ (self, port: int , backlog: int) -> None:

        self.__class__.port = port
        self.__class__.backlog = backlog

        return

class ViewConnection(Connection):

    def __init__ (self, port: int | None = None, backlog: int = 4) -> None:

        if self.__class__.port is None:
            super().__init__(port or 53881, backlog)

        return

class Server():

    # the subclasses should be a subclass of Connection
    # and should set these values
    # port: int | None
    # backlog: int

    server: socket.socket | None = None

    thread_list: List[threading.Thread] = []

    def __init__ (self) -> None:

        server: socket.socket

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((socket.gethostname(), self.port))
        server.listen(self.backlog)

        self.__class__.server = server

        return

    # Subclasses should implement this method
    def payload_handler(self, client: socket.socket, payload: bytearray) -> bool:

        return False

    def thread_handler (self, client: socket.socket) -> None:

        buf: bytearray
        msg: bytearray
        size: int
        left_to_recv: int

        while True:

            buf = client.recv(4)
            # TODO: use a loop for each byte
            if len(buf) < 4 :
                print("Client got disconnected")
                print("Leaving the thread")
                break

            size = buf[0] | buf[1] << 8 | buf[2] << 16 | buf[3] << 24
            left_to_recv = size

            msg = bytearray([])

            while left_to_recv > 0:

                buf = client.recv(left_to_recv)
                if buf == bytearray([]):
                    break
                else:
                    msg = msg + buf
                    left_to_recv -= len(buf)

            if len(msg) != size:
                print("Client got disconnected")
                print("Leaving the thread")
                break

            # call the payload_handler from here

            if not self.payload_handler(client, msg):
                print("payload_handeler returned False, stopping the thread")
                break

    def start (self) -> None:

        connected_client: socket.socket
        thread: threading.Thread

        # TODO: Limit the number of threads, maybe to 20
        while True:
            # this will block
            connected_client, _ = self.server.accept()

            thread = threading.Thread(
                target = self.thread_handler, args = [connected_client]
            )
            thread.start()
            self.thread_list.append(thread)

        return

class ViewServer(Server, ViewConnection):

    command: str | None = None

    def __init__ (
        self,
        port: int | None = None,
        command: str | None = None,
        backlog: int = 4
    ) -> None:

        if self.__class__.server is None:

            ViewConnection.__init__(self, port = port, backlog = backlog)
            Server.__init__(self)

            self.__class__.command = command or "termux-share"

        return

    def payload_handler (
        self,
        client: socket.socket,
        payload: bytearray
    ) -> bool:

        # the payload should be the relative path from the home dirctory
        # or an absolute path
        file: str = payload.decode()

        if file[0] != "/":
            # relative path from home
            file = os.environ["HOME"] + "/" + file

        dir: str = re.sub("[^/]*$", "", file)

        if dir != "" and pathlib.Path(dir).is_dir():
            if pathlib.Path(file).is_file():
                os.chdir(dir)
                print("Opening: \"" + file + "\"")
                os.system(self.command + " \"" + file + "\"")
            else:
                print("File does not exists: \"" + file + "\"")
        else:
            print("Directory does not exists: \"" + dir + "\"")

        return True

class Client():

    server: socket.socket | None = None

    def __init__ (self) -> None:

        self.__class__.server = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )

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

    def send (self, payload: str) -> None:

        size: int
        buf: bytearray

        size = len(file)

        buf = bytearray([
            size & 0xff, (size >> 8) & 0xff, (size >> 16) & 0xff, (size >> 24) & 0xff
        ]) + payload.encode()

        self.server.send(buf)

        return

class ViewClient(ViewConnection):

    def __init__ (self, port: int | None = None) -> None:

        if self.server is None:
            ViewConnection.__init__(self, port = port)
            Client.__init__(self)

        return

    def view (self, file: str) -> None:

        path: pathlib.PosixPath

        path = pathlib.Path(file)

        if not path.is_file():
            raise Execption("File does not exists")
            return
        else:
            path = path.resolve()

        file = re.sub("^" + os.environ["HOME"] + "/", "", str(path))

        self.send(file)

        return
