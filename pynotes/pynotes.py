import socket
import os

class ViewConnection():

    port: int | None = None

    def __init__ (self, port: int | None = None) -> None:

        if ViewConnection.port is None:
            ViewConnection.port = port or 52886

        return
