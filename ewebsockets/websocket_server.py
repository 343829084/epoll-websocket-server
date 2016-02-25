#!/bin/env python3

import esockets
import logging
from .RFC6455 import *
from .ClientSocket import Client


class Websocket:
    def __init__(self,
                 handle_new_connection=lambda client: True,
                 handle_websocket_frame=lambda client, frame: True,
                 esockets_kwargs={}):

        self.handle_new_connection = handle_new_connection
        self.handle_websocket_frame = handle_websocket_frame

        kwargs = dict(esockets_kwargs)
        kwargs.update({'handle_incoming': self._handle_incoming})
        kwargs.update({'handle_readable': self._handle_readable})
        self.server = esockets.SocketServer(**kwargs)

        self.clients = {}

    def _handle_incoming(self, sock, address):
        """The esockets required function for handling incoming client connections
        """
        client = Client(sock, address)
        if self.handle_new_connection(client):
            self.clients[sock] = client
            return True
        return False

    def _handle_readable(self, sock):
        """The esockets required function for handling incoming data from clients
        """
        client_obj = self.clients[sock]
        if client_obj.state == Client.CONNECTING:
            return client_obj.do_handshake()

        elif client_obj.state == Client.OPEN or client_obj.state == Client.CLOSING:
            frame = client_obj.recv_frame()
            if frame.fin == 1:
                # Let the user handle a finished frame
                self.handle_websocket_frame(client_obj, frame)

            if frame.opcode == OpCode.CLOSE:
                del self.clients[sock]
                return False
            else:
                return True

    def start(self):
        self.server.start()

    def clients_list(self):
        return list(self.clients.values())
