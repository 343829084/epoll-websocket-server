#!/bin/env python3

import esockets
import socket
import logging
from .RFC6455 import *
from .bytes_convert import *
from threading import Lock, Condition
from .ClientSocket import *

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
        client = Client(sock, address)
        if self.handle_new_connection(client):
            self.clients[sock] = client
            return True
        return False

    def _handle_readable(self, sock):
        client_obj = self.clients[sock]
        if client_obj.state == Client.CONNECTING:
            handshake = client_obj.recv(4096)
            logging.debug('{}: Received handshake'.format(client_obj.address))
            try:
                response = pack_handshake(handshake)
            except DataMissing:
                logging.warning('{}: Received unaccepted handshake'.format(client_obj.address))
                return False
            else:
                total_sent = client_obj.send(response, timeout=10)
                if total_sent == len(response):
                    client_obj.state = Client.OPEN
                    logging.debug('{}: Handshake complete, client now in open state'.format(client_obj.address))
                    return True
                else:
                    logging.warning('{}: Handshake failed, {}/{} bytes of the response sent'.format(client_obj.address, total_sent, len(response)))
                    return False

        elif client_obj.state == Client.OPEN:
            frame = client_obj.recv_frame()
            frame.mask = 1
            print('FRAME: ', frame.pack())
            self.handle_websocket_frame(client_obj, frame)
            if frame.opcode == OpCode.CLOSE:
                return False
            else:
                return True

    def start(self):
        self.server.start()

    def _send(self, client, data):
        return client.sendall(data)
