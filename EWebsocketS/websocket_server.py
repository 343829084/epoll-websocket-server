#!/bin/env python3

import ESocketS
from .RFC6455 import *
from .bytes_convert import *

class Client:
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3
    def __init__(self):
        self.state = self.CONNECTING


class Websocket:
    def __init__(self,
                 port=1234,
                 host=socket.gethostbyname(socket.gethostname()),
                 queue_size=1000,
                 handle_new_connection=lambda client, address: True,
                 handle_websocket_frame=lambda client, frame: True):

        self.handle_new_connection = handle_new_connection
        self.handle_websocket_frame = handle_websocket_frame

        self.clients = {}

        self.server = ESocketS.SocketServer(port=port,
                                            host=host,
                                            queue_size=queue_size,
                                            handle_readable=self._handle_readable,
                                            handle_incoming=self._handle_incoming)
        self.server.start()

    def _handle_incoming(self, client, address):
        if self.handle_new_connection(client, address):
            self.clients[client] = Client()
            return True

        return False

    def _handle_readable(self, client):
        state = self.clients[client].state
        if state == Client.CONNECTING:
            try:
                self._recv_and_send_handshake(client)
                self.clients[client].state = Client.OPEN
                return True
            except(DataMissing, ClientDisconnect, socket.error):
                return False

        elif state == Client.OPEN:
            try:
                frame = self._recv_websocket_frame(client)
                return self.handle_websocket_frame(client, frame)
            except(DataMissing, FrameError):
                return True
            except(ClientDisconnect, socket.error):
                return False


    def _recv_websocket_frame(self, client):

        frame_head = self._recv(client, 2)
        FIN = frame_head[0] >> 7
        RSV = (frame_head[0] >> 6 & 0b00000001,
               frame_head[0] >> 5 & 0b00000001,
               frame_head[0] >> 4 & 0b00000001)

        opcode = bytes(int2bytes(frame_head[0] & 0b00001111, 1))

        if not OC.is_valid(opcode):
            raise FrameError('Opcode: {} is not recognized'.format(opcode))

        mask = frame_head[1] >> 7
        payload_len = frame_head[1] & 0b01111111

        if payload_len == 126:
            payload_len = bytes2int(self._recv(client, 2))
        elif payload_len == 127:
            payload_len = bytes2int(self._recv(client, 8))

        masking_key = None
        if mask:
            masking_key = self._recv(client, 4)

        payload = self._recv(client, payload_len)

        if mask:
            payload = masking_algorithm(payload, masking_key)

        return Frame(FIN, RSV, opcode, mask, payload, masking_key)

    def _recv_and_send_handshake(self, client):
        opening_handshake = self._recv(client, 4096, False)
        closing_handshake = pack_handshake(opening_handshake)
        self._send(client, closing_handshake)

    def _recv(self, client, size, all=True):
        data = client.recv(size)
        if data == b'':
            raise ClientDisconnect

        if all and len(data) != size:
            raise DataMissing('Expected to receive {} bytes but '
                              'only found {} bytes in the buffer'.format(size, len(data)))

        return data

    def _send(self, client, data):
        return client.sendall(data)

# class Websocket(ESocketS.Socket):
#     def __init__(self,
#                  port=ESocketS.SocketServer.__init__.__defaults__[0],
#                  host=ESocketS.SocketServer.__init__.__defaults__[1],
#                  clients_class=Connection):
#
#         ESocketS.Socket.__init__(self,
#                                  port=port,
#                                  host=host,
#                                  clients_class=clients_class,
#                                  auto_register=False)
#
#         self.recv_handlers = {Connection.CONNECTING: self.handle_client_handshake,
#                               Connection.OPEN: self.handle_websocket_frame}
#
#         self.websocket_frame_handlers = {RFC6455.OC.CONTINUATION: self.handle_continuation,
#                                          RFC6455.OC.TEXT: self.handle_text,
#                                          RFC6455.OC.BINARY: self.handle_binary,
#                                          RFC6455.OC.CLOSE: self.handle_close,
#                                          RFC6455.OC.PING: self.handle_ping,
#                                          RFC6455.OC.PONG: self.handle_pong }
#
#     # ------------------- ESocketS "on" functions --------------------
#     def on_recv(self, fileno, data):
#         self.recv_handlers[self.clients[fileno].state](fileno, data)
#
#     def on_disconnect(self, fileno):
#         self.close(fileno)
#         self._on_abnormal_disconnect(fileno, 'Received empty bytearray')
#
#     def on_abnormal_disconnect(self, fileno, msg):
#         self.close(fileno)
#         self._on_abnormal_disconnect(fileno, msg)
#     # ----------------------------------------------------------------
#
#     # ------------------- recv handlers ------------------------------
#     def handle_client_handshake(self, fileno, handshake):
#         try:
#             handshake_responce = RFC6455.pack_handshake(handshake)
#             self.send(fileno, handshake_responce)
#             self.register(fileno)
#             self.clients[fileno].state = Connection.OPEN
#             self.on_client_open(fileno)
#         except RFC6455.DataMissing:
#             raise InvalidHandshake('Received invalid handshake from %s' % self.clients[fileno].getip())
#
#     def handle_websocket_frame(self, fileno, frame):
#         try:
#             fobj = RFC6455.WSframe(frame)
#             fobj.unpack()
#             if fobj.FIN == 0:
#                 if fobj.opcode != RFC6455.OC.CONTINUATION:
#                     self.clients[fileno].fragm[0] = fobj.opcode
#                 self.clients[fileno].fragm[1] += fobj.payload
#             else:
#                 self.websocket_frame_handlers[fobj.opcode](fileno, fobj.payload)
#
#             if fobj.opcode != RFC6455.OC.CLOSE:
#                 self.register(fileno)
#
#         except RFC6455.InvalidFrame:
#             raise InvalidWebsocketFrame('Received invalid websocket frame from %s' % self.clients[fileno].getip())
#
#     # ----------------------------------------------------------------
#
#     # ----------------- websocket frame handlers ---------------------
#
#     def handle_continuation(self, fileno, payload):
#         final_opcode = self.clients[fileno].fragm[0]
#         entire_payload = self.clients[fileno].fragm[1] + payload
#         self.clients[fileno].fragm = [b'', b'']
#         self.handle_websocket_frame[final_opcode](fileno, entire_payload)
#
#     def handle_text(self, fileno, payload):
#         self.on_text_recv(fileno, payload)
#
#     def handle_binary(self, fileno, payload):
#         self.on_binary_recv(fileno, payload)
#
#     def handle_close(self, fileno, payload):
#         if self.clients[fileno].state == Connection.OPEN:
#             self.clients[fileno].state = Connection.CLOSING
#             frame = RFC6455.WSframe(opcode=RFC6455.OC.CLOSE,
#                                     payload=payload)
#             frame.pack()
#             self.send(fileno, frame.frame)
#
#         self.close(fileno)
#         self.on_normal_disconnect(fileno, payload)
#
#     def handle_ping(self, fileno, payload):
#         frame = RFC6455.WSframe(opcode=RFC6455.OC.PONG,
#                                 payload=payload)
#         frame.pack()
#         self.send(fileno, frame.frame)
#         self.on_ping_recv(fileno, payload)
#
#     def handle_pong(self, fileno, payload):
#         self.on_pong_recv(fileno, payload)
#
#     # --------------------------------------------------------------
#
#
#     # -------------------The "on" functions -------------------------
#     def on_client_open(self, fileno):
#         pass
#
#     def on_text_recv(self, fileno, text):
#         pass
#
#     def on_binary_recv(self, fileno, binary):
#         pass
#
#     def on_close_recv(self, fileno, reason):
#         pass
#
#     def on_ping_recv(self, fileno, payload):
#         pass
#
#     def on_pong_recv(self, fileno, payload):
#         pass
#
#     def on_normal_disconnect(self, fileno, reason):
#         pass
#
#     def _on_abnormal_disconnect(self, fileno, msg):
#         pass
#     # ---------------------------------------------------------------
