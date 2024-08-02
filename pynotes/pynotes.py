import socket
import os

class LaunchConnection():

    port: int | None = None

    def __init__ (self, port: int | None = None) -> None:

        if LaunchConnection.port is None:
            LaunchConnection.port = port or 52886

        return
