import contextlib
import threading
import pathlib
import socket
import json
import os
import re
import io

from typing import List, Dict

class Connection():

    port: int | None = None
    backlog: int

    def __init__ (self, port: int , backlog: int) -> None:

        self.__class__.port = port
        self.__class__.backlog = backlog

        return

    def recv (self, sender: socket.socket) -> bytearray:

        buf: bytearray
        payload: bytearray
        size: int
        left_to_recv: int

        buf = sender.recv(4)
        # TODO: use a loop for each byte
        if len(buf) < 4 :
            raise Exception(
                "Got disconnected from the server, while recv 'ing size"
            )

        size = buf[0] | buf[1] << 8 | buf[2] << 16 | buf[3] << 24
        left_to_recv = size

        payload = bytearray([])

        while left_to_recv > 0:

            buf = sender.recv(left_to_recv)
            if buf == bytearray([]):
                break
            else:
                payload = payload + buf
                left_to_recv -= len(buf)

        if len(payload) != size:
            raise Exception(
                "Got disconnected from the server, while recv 'ing payload"
            )

        return payload

    def send (self, payload: bytearray, receiver: socket.socket) -> None:

        size: int
        buf: bytearray

        size = len(payload)

        buf = bytearray([
            size & 0xff, (size >> 8) & 0xff, (size >> 16) & 0xff, (size >> 24) & 0xff
        ]) + payload

        receiver.send(buf)

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

        payload: bytearray

        while True:

            try:
                payload = self.recv(sender = client)
            except:
                break
            else:
                if not self.payload_handler(client, payload):
                    print("payload_handler returned False, stopping the thread")
                    break

        return

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
            return True

        return False

class ViewClient(Client, ViewConnection):

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

        self.send(payload = file.encode(), receiver = self.server)

        return

class ExecConnection(Connection):

    def __init__ (self, port: int | None = None, backlog: int = 4) -> None:

        if self.__class__.port is None:
            super().__init__(port or 46821, backlog)

        return

class ExecServer(Server, ExecConnection):

    def __init__ (
        self,
        port: int | None = None,
        backlog: int = 4
    ) -> None:

        if self.__class__.server is None:

            ExecConnection.__init__(self, port = port, backlog = backlog)
            Server.__init__(self)

        return

    # the client will send the file name, the server will exec the file
    # then send the stdout back to the client through the same socket
    def payload_handler (
        self,
        client: socket.socket,
        payload: bytearray
    ) -> bool:
        """
        The result of the exec will be a serialized dictionary
        {
            stdout_file_name: path to the file,
            exec_status: whether the exec succeded or not,
        }
        """

        # the payload should be the relative path from the home dirctory
        # or an absolute path
        file: str = payload.decode()

        stdout_file_name: str
        stdout_file: io.TextIOWrapper
        script_file: io.TextIOWrapper

        payload: Dict[str, str] = {
            "stdout_file_name": "",
            "exec_status": "FAILED",
        }

        stdout: io.StringIO = io.StringIO()

        if file[0] != "/":
            # relative path from home
            file = os.environ["HOME"] + "/" + file

        dir: str = re.sub("[^/]*$", "", file)

        if dir != "" and pathlib.Path(dir).is_dir():
            if pathlib.Path(file).is_file():
                os.chdir(dir)

                stdout_file_name = re.sub(r"\.py$", ".stdout", file)

                print("Exec 'ing " + file)

                try:
                    with contextlib.redirect_stdout(stdout):
                        with open(file) as script_file:
                            exec(script_file.read())
                except:
                    print("Exec failed")
                else:
                    print("Done exec 'ing")
                    payload["exec_status"] = "SUCCESS"
                    if stdout.getvalue() != "":
                        with open(stdout_file_name, "w") as stdout_file:
                            stdout_file.write(stdout.getvalue())
                        payload["stdout_file_name"] = re.sub(
                            "^" + os.environ["HOME"] + "/", "", stdout_file_name
                        )
                    else:
                        try:
                            os.remove(stdout_file_name)
                        except:
                            pass


            else:
                print("File does not exists: \"" + file + "\"")
        else:
            print("Directory does not exists: \"" + dir + "\"")

        self.send(
            payload = json.dumps(payload).encode(),
            receiver = client
        )

        # send the payload from here

        return True

class ExecClient(Client, ExecConnection):

    def __init__ (self, port: int | None = None) -> None:

        if self.server is None:
            ExecConnection.__init__(self, port = port)
            Client.__init__(self)

        return

    def exec (self, file: str) -> str:

        path: pathlib.PosixPath
        stdout_file: io.TextIOWrapper
        payload: Dict[str, str]
        stdout: str

        path = pathlib.Path(file)

        if not path.is_file():
            raise Execption("File does not exists")
            return
        else:
            path = path.resolve()

        file = re.sub("^" + os.environ["HOME"] + "/", "", str(path))

        self.send(payload = file.encode(), receiver = self.server)

        payload = json.loads(self.recv(sender = self.server).decode())

        if payload["exec_status"] == "FAILED":
            raise Execption("Exec Failed")

        if payload["stdout_file_name"] != "":

            with open(os.environ["HOME"] + "/" + payload["stdout_file_name"]) as stdout_file:
                stdout = stdout_file.read()

        return stdout
