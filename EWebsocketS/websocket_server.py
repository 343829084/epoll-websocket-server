 #!/bin/env python3
import ESocketS
from EWebsocketS.connection import Connection
import EWebsocketS.RFC6455 as RFC6455
import socket
from threading import Thread


class Websocket(ESocketS.Socket):
    def __init__(self,
                 port=ESocketS.Socket.__init__.__defaults__[0],
                 host=ESocketS.Socket.__init__.__defaults__[1],
                 clients_class=Connection):

        ESocketS.Socket.__init__(self,
                                 port=port,
                                 host=host,
                                 clients_class=clients_class,
                                 auto_register=False)

        self.recv_handlers = {Connection.CONNECTING: self.handle_client_handshake,
                              Connection.OPEN: self.handle_websocket_frame}

        self.websocket_frame_handlers = {RFC6455.OC.CONTINUATION: self.handle_continuation,
                                         RFC6455.OC.TEXT: self.handle_text,
                                         RFC6455.OC.BINARY: self.handle_binary,
                                         RFC6455.OC.CLOSE: self.handle_close,
                                         RFC6455.OC.PING: self.handle_ping,
                                         RFC6455.OC.PONG: self.handle_pong }

    # ------------------- ESocketS "on" functions --------------------
    def on_recv(self, fileno, data):
        self.recv_handlers[self.clients[fileno].state](fileno, data)

    def on_disconnect(self, fileno):
        self.close(fileno)
        self._on_abnormal_disconnect(fileno, 'Received empty bytearray')

    def on_abnormal_disconnect(self, fileno, msg):
        self.close(fileno)
        self._on_abnormal_disconnect(fileno, msg)
    # ----------------------------------------------------------------

    # ------------------- recv handlers ------------------------------
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
