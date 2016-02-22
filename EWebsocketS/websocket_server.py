#!/bin/env python3

import esockets
import socket
import logging
from .RFC6455 import *
from .bytes_convert import *


class Client:
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3

    def __init__(self, address):
        self.state = self.CONNECTING
        self.address = address
        self.close_frame_sent = False


class Websocket:
    def __init__(self,
                 handle_new_connection=lambda client, address: True,
                 handle_websocket_frame=lambda client, frame: True,
                 esockets_kwargs={}):

        self.handle_new_connection = handle_new_connection
        self.handle_websocket_frame = handle_websocket_frame

        kwargs = dict(esockets_kwargs)
        kwargs.update({'handle_incoming': self._handle_incoming})
        kwargs.update({'handle_readable': self._handle_readable})
        self.server = esockets.SocketServer(**kwargs)

        self.clients = {}

    def _handle_incoming(self, client, address):
        if self.handle_new_connection(client, address):
            self.clients[client] = Client(address)
            return True
        return False

    def _handle_readable(self, client):
        client_obj = self.clients[client]
        if client_obj.state == Client.CONNECTING:
            handshake = self._recv(client, 4096, forceAll=False)
            try:
                response = pack_handshake(handshake)
            except DataMissing:
                logging.warning('Received unaccepted handshake from %s', client_obj.address)
                return False
            else:
                self._send(client, response)
                self.clients[client].state = Client.OPEN
                logging.debug('%s: Handshake complete, client now in open state', client_obj.address)
                return True

        elif client_obj.state == Client.OPEN:
            frame_head = self._recv(client, 2)
            frame = read_frame_head(frame_head)
            if frame.payload_len == 126:
                frame.payload_len_ext = bytes2int(self._recv(client, 2))
            elif frame.payload_len == 127:
                payload_len_ext = bytes2int(self._recv(client, 8))

            if frame.mask:
                frame.masking_key = self._recv(client, 4)

            frame.payload = self._recv(client, frame.payload_len_ext or frame.payload_len)

            if frame.mask:
                frame.unmasked_payload = masking_algorithm()



    def _recv(self, client, size, forceAll=True):
        data = client.recv(size)
        if data == b'':
            raise ClientDisconnect

        if forceAll and len(data) != size:
            raise DataMissing('Expected to receive {} bytes but '
                              'only found {} bytes in the buffer'.format(size, len(data)))
        return data

    def _send(self, client, data):
        return client.sendall(data)

# class Websocket:
#     def __init__(self,
#                  port=1234,
#                  host=socket.gethostbyname(socket.gethostname()),
#                  queue_size=1000,
#                  handle_new_connection=lambda client, address: True,
#                  handle_websocket_frame=lambda client, frame: True):
#
#         self.handle_new_connection = handle_new_connection
#         self.handle_websocket_frame = handle_websocket_frame
#
#         self.clients = {}
#
#         self.server = esockets.SocketServer(port=port,
#                                             host=host,
#                                             queue_size=queue_size,
#                                             handle_readable=self._handle_readable,
#                                             handle_incoming=self._handle_incoming)
#
#     def _handle_incoming(self, client, address):
#         if self.handle_new_connection(client, address):
#             self.clients[client] = Client(address)
#             return True
#         return False
#
#     def _handle_readable(self, client):
#         client_obj = self.clients[client]
#
#         if client_obj.state == Client.CONNECTING:
#             handshake = self._recv(client, 4096, forceAll=False)
#             try:
#                 response = pack_handshake(handshake)
#             except DataMissing:
#                 logging.error('Received unaccepted handshake from %s', client_obj.address)
#                 return False
#             else:
#                 self._send(client, response)
#                 self.clients[client].state = Client.OPEN
#                 logging.debug('%s: Handshake complete, client now in open state', client_obj.address)
#                 return True
#         else:
#             try:
#                 frame = self._recv_websocket_frame(client)
#             except ClientDisconnect:
#                 return False
#             else:
#                 return self.handle_websocket_frame(client, frame)
#
#     def _recv(self, client, size, forceAll=True):
#         data = client.recv(size)
#         if data == b'':
#             raise ClientDisconnect
#
#         if forceAll and len(data) != size:
#             raise DataMissing('Expected to receive {} bytes but '
#                               'only found {} bytes in the buffer'.format(size, len(data)))
#
#         return data
#
#     def _send(self, client, data):
#         return client.sendall(data)
#
#     def _recv_websocket_frame(self, client):
#
#         frame_head = self._recv(client, 2)
#         FIN = frame_head[0] >> 7
#         RSV = (frame_head[0] >> 6 & 0b00000001,
#                frame_head[0] >> 5 & 0b00000001,
#                frame_head[0] >> 4 & 0b00000001)
#
#         opcode = bytes(int2bytes(frame_head[0] & 0b00001111, 1))
#
#         if not OC.is_valid(opcode):
#             raise FrameError('Opcode: {} is not recognized'.format(opcode))
#
#         mask = frame_head[1] >> 7
#         payload_len = frame_head[1] & 0b01111111
#
#         if payload_len == 126:
#             payload_len = bytes2int(self._recv(client, 2))
#         elif payload_len == 127:
#             payload_len = bytes2int(self._recv(client, 8))
#
#         masking_key = None
#         if mask:
#             masking_key = self._recv(client, 4)
#
#         payload = self._recv(client, payload_len)
#
#         if mask:
#             payload = masking_algorithm(payload, masking_key)
#
#         return Frame(FIN, RSV, opcode, mask, payload, masking_key)
#
#     def start(self):
#         self.server.start()
#
#     def stop(self):
#         self.server.stop()