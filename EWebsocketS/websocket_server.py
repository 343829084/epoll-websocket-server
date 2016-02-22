 #!/bin/env python3
import ESocketS
import EWebsocketS.RFC6455 as RFC6455
import threading
from EWebsocketS.bytes_convert import *


class _Client:
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3

    def __init__(self):
        self._state = self.CONNECTING
        self._fragments = [b'', b'']

    def set_state(self, state):
        if state in range(4):
            self._state = state
        else:
            raise ValueError('{} is not a recognized state'.format(state))

    def get_state(self):
        return self._state


class Websocket(ESocketS.Socket):
    def __init__(self, **kwargs):

        ESocketS.Socket.__init__(self, **kwargs)



        self.recv_handlers = {_Client.CONNECTING: self.handle_client_handshake,
                              _Client.OPEN: self.handle_websocket_frame}

        self.websocket_frame_handlers = {RFC6455.OC.CONTINUATION: self.handle_continuation,
                                         RFC6455.OC.TEXT: self.handle_text,
                                         RFC6455.OC.BINARY: self.handle_binary,
                                         RFC6455.OC.CLOSE: self.handle_close,
                                         RFC6455.OC.PING: self.handle_ping,
                                         RFC6455.OC.PONG: self.handle_pong }

        self._clients = {}

    # ------------------- ESocketS "on" functions --------------------
    def on_disconnect(self, fileno):
        self.close(fileno)
        self._on_abnormal_disconnect(fileno, 'Received empty bytearray')

    def on_abnormal_disconnect(self, fileno, msg):
        self.close(fileno)
        self._on_abnormal_disconnect(fileno, msg)
    # ----------------------------------------------------------------


    # ------------------- recv handlers ------------------------------

    def _recv_websocket_frame(self, conn):
        head = self.recv_raw(conn, 2)
        payload_len = head[1] & 0b01111111
        mask =  head[1] & 0b10000000
        if payload_len == 126:
            payload_len = bytes2int(self.recv_raw(conn, 2))
        elif payload_len == 127:
            payload_len = bytes2int(self.recv_raw(conn, 8))

        if mask:
            mask_key = self.recv_raw(conn, 4)
        else:
            mask_key = b''

        payload = self.recv_raw(conn, payload_len)

        return
        self.handle_websocket_frame(conn, )

        return

    def handle_client_handshake(self, fileno, handshake):
        try:
            handshake_responce = RFC6455.pack_handshake(handshake)
            self.send(fileno, handshake_responce)
            self.register(fileno)
            self.clients[fileno].state = Connection.OPEN
            self.on_client_open(fileno)
        except RFC6455.DataMissing:
            raise InvalidHandshake('Received invalid handshake from %s' % self.clients[fileno].getip())

    def handle_websocket_frame(self, fileno, frame):
        try:
            fobj = RFC6455.WSframe(frame)
            fobj.unpack()
            if fobj.FIN == 0:
                if fobj.opcode != RFC6455.OC.CONTINUATION:
                    self.clients[fileno].fragm[0] = fobj.opcode
                self.clients[fileno].fragm[1] += fobj.payload
            else:
                self.websocket_frame_handlers[fobj.opcode](fileno, fobj.payload)

            if fobj.opcode != RFC6455.OC.CLOSE:
                self.register(fileno)

        except RFC6455.InvalidFrame:
            raise InvalidWebsocketFrame('Received invalid websocket frame from %s' % self.clients[fileno].getip())

    # ----------------------------------------------------------------

    # ----------------- websocket frame handlers ---------------------

    def handle_continuation(self, fileno, payload):
        final_opcode = self.clients[fileno].fragm[0]
        entire_payload = self.clients[fileno].fragm[1] + payload
        self.clients[fileno].fragm = [b'', b'']
        self.handle_websocket_frame[final_opcode](fileno, entire_payload)

    def handle_text(self, fileno, payload):
        self.on_text_recv(fileno, payload)

    def handle_binary(self, fileno, payload):
        self.on_binary_recv(fileno, payload)

    def handle_close(self, fileno, payload):
        if self.clients[fileno].state == Connection.OPEN:
            self.clients[fileno].state = Connection.CLOSING
            frame = RFC6455.WSframe(opcode=RFC6455.OC.CLOSE,
                                    payload=payload)
            frame.pack()
            self.send(fileno, frame.frame)

        self.close(fileno)
        self.on_normal_disconnect(fileno, payload)

    def handle_ping(self, fileno, payload):
        frame = RFC6455.WSframe(opcode=RFC6455.OC.PONG,
                                payload=payload)
        frame.pack()
        self.send(fileno, frame.frame)
        self.on_ping_recv(fileno, payload)

    def handle_pong(self, fileno, payload):
        self.on_pong_recv(fileno, payload)

    # --------------------------------------------------------------


    # -------------------The "on" functions -------------------------
    def on_client_open(self, fileno):
        pass

    def on_text_recv(self, fileno, text):
        pass

    def on_binary_recv(self, fileno, binary):
        pass

    def on_close_recv(self, fileno, reason):
        pass

    def on_ping_recv(self, fileno, payload):
        pass

    def on_pong_recv(self, fileno, payload):
        pass

    def on_normal_disconnect(self, fileno, reason):
        pass

    def _on_abnormal_disconnect(self, fileno, msg):
        pass
    # ---------------------------------------------------------------


class InvalidHandshake(Exception):
    pass


class InvalidWebsocketFrame(Exception):
    pass
