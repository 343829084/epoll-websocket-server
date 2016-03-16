#!/bin/env python3

import esockets
import logging
from .RFC6455 import *
from .ClientSocket import Client


class Websocket:
    def __init__(self,
                 handle_new_connection=lambda client: True,
                 handle_websocket_frame=lambda client, frame: True,
                 on_client_open=lambda client: True,
                 on_client_close=lambda client: True,
                 esockets_kwargs={}):

        self.handle_new_connection = handle_new_connection
        self.handle_websocket_frame = handle_websocket_frame
        self.on_client_open = on_client_open
        self.on_client_close = on_client_close

        kwargs = dict(esockets_kwargs)
        kwargs.update({'handle_incoming': self._handle_incoming})
        kwargs.update({'handle_readable': self._handle_readable})
        self.server = esockets.SocketServer(**kwargs)

        self.clients = {}

    def _handle_incoming(self, sock, address):
        """The esockets required function for handling incoming client connections
        """
        client = Client(sock, address,
                        on_open=self.on_client_open,
                        on_close=self.on_client_close)
        if self.handle_new_connection(client):
            self.clients[sock] = client
            return True
        return False

    def _handle_readable(self, sock):
        """The esockets required function for handling incoming data from clients
        """
        client_obj = self.clients[sock]
        if client_obj.state == Client.CONNECTING:
            # handshake_success = client_obj.do_handshake()
            # if handshake_success:
            #     self.on_client_open(client_obj)
            # return handshake_success
            return client_obj.do_handshake()
        elif client_obj.state == Client.OPEN or client_obj.state == Client.CLOSING:
            frame = client_obj.recv_frame()
            if not OpCode.is_valid(frame.opcode):
                self.close_connection(sock)
                logging.info('{}: Closing connection, invalid opcode: {}'.format(client_obj.address, frame.opcode))
                return False

            if frame.fin == 1:
                # Let the user handle a finished frame
                if not self.handle_websocket_frame(client_obj, frame):
                    # if handle_websocket_frame returns false send close frame and emedietely disconnect user
                    logging.info('{}: Closing connection because handle_websocket_frame returned false'.format(client_obj.address))
                    self.close_connection(sock)
                    return False

            if frame.opcode == OpCode.CLOSE:
                del self.clients[sock]
                return False
            else:
                return True

    def start(self):
        self.server.start()

    def stop(self):
        for client in self.clients_list():
            self.close_connection(client)

        self.server.stop()

    def clients_list(self):
        return list(self.clients.values())

    def close_connection(self, client, status_code=StatusCode.PROTOCOL_ERROR, reason=b''):
        try:
            client.close(status_code=status_code, timeout=0, reason=reason)
        finally:
            self.server.disconnect(client.socket)
            del self.clients[client.socket]

    def send_text(self, client, text, timeout=-1, mask=0):
        try:
            client.send_text(text, timeout, mask)
        except (OSError, BrokenPipeError, ClientDisconnect):
            self.close_connection(client, StatusCode.ENDP_GOING_AWAY, b'Broken pipe')
            logging.error('{}: Broken pipe'.format(client.address))

