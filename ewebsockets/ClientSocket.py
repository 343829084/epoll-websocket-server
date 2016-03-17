#!/bin/env python3

from threading import Lock, Event
from .exceptions import *
from .RFC6455 import *
import logging
from json import JSONEncoder
from esockets import ConnectionBroken
import esockets


class Client(esockets.Client):
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3
    _states = {CONNECTING: 'Connecting',
               OPEN: 'Open',
               CLOSING: 'Closing',
               CLOSED: 'Closed'}

    def __init__(self, sock, address):
        esockets.Client.__init__(self, sock, address)
        self.state = Client.CONNECTING
        self.close_frame_sent = False

    # def __init__(self, sock,
    #              on_open=lambda client: True,
    #              state=0):
    #
    #     self.socket = sock  # the client from esockets
    #
    #     self.state = state
    #     # self.address = esockets_client.address
    #     self.close_frame_sent = False
    #     self.close_frame_recd = False
    #     self.send_lock = Lock()
    #     self.close_lock = Event()
    #     self.unfinished_frame = None
    #
    #     self.on_open = on_open

    # def address(self):
    #     return self.socket.address

    # def send_raw(self, msg, timeout=-1):
    #     total_sent = 0
    #     msg_len = len(msg)
    #     if self.send_lock.acquire(timeout=timeout):
    #         try:
    #             while total_sent < msg_len:
    #                 sent = self.socket.send(msg[total_sent:])
    #                 if sent == 0:
    #                     raise ClientDisconnect("Socket connection broken")
    #                 total_sent = total_sent + sent
    #         finally:
    #             self.send_lock.release()
    #     return total_sent

    def handle_message(self):


    def handle_payload(self):


    def do_handshake(self):
        """
        :return:True/False (Success/Failed handshake)
        """
        client_handshake = self.recv(4096, fixed=False)
        logging.debug('{}: Received handshake'.format(self.address()))
        try:
            response = pack_handshake(client_handshake)
        except DataMissing:
            logging.warning('{}: Received unaccepted handshake'.format(self.address()))
            self.socket.close('Received unaccepted handshake')  # just close the socket
            # because the handshake was not complete no RFC6455 protocol needs to be followed here
        else:
            self.socket.send(response, timeout=5)
            # if total_sent == len(response):
            self.state = Client.OPEN
            self.on_open(self)
            logging.debug('{}: Handshake complete, client now in open state'.format(self.address()))
            # return True
            # else:
            #     logging.warning('{}: Handshake failed, {}/{} bytes of the response sent'.format(self.address(),
            #                                                                                     total_sent,
            #                                                                                     len(response)))
            #     return False

    def send(self, bytes, timeout=-1):
        return self.socket.send(bytes, timeout)

    # def send_frame(self, frame, timeout=-1):
    #     return self.send(frame.pack(), timeout)

    def send_text(self, text, timeout=-1, mask=0):
        if type(text) == str:
            frame = Frame(payload=text.encode(),
                          opcode=OpCode.TEXT,
                          mask=mask)
        else:
            frame = Frame(payload=text,
                          opcode=OpCode.TEXT,
                          mask=mask)
        return self.send(frame.pack(), timeout)

    def send_binary(self, bytes, timeout=-1, mask=0):
        frame = Frame(payload=bytes,
                      opcode=OpCode.BINARY,
                      mask=mask)
        self.send_frame(frame, timeout)

    # def send_json(self, json_obj, timeout=-1, mask=0):
    #     self.send_text(JSONEncoder().encode(json_obj), timeout, mask)

    # def recv_all(self, size, chunk_size=2048):
    #     data = bytearray(size)
    #     bytes_recd = 0
    #
    #     while bytes_recd < size:
    #         to_recv = min(size-bytes_recd, chunk_size)
    #         try:
    #             chunk = self.recv(to_recv)
    #         except BlockingIOError:
    #             raise DataMissing('Expected to receive {} bytes but '
    #                               'only found {} bytes in the buffer'.format(size, bytes_recd))
    #         else:
    #             if len(chunk) != to_recv:
    #                 raise DataMissing('Expected to receive {} bytes but '
    #                                   'only found {} bytes in the buffer'.format(size, bytes_recd))
    #
    #             data[bytes_recd:bytes_recd+to_recv] = chunk
    #             bytes_recd += len(chunk)
    #     return data

    def recv(self, size, fixed=True):
        return self.socket.recv(size, fixed)
        # data = self.socket.recv(size)
        # if data == b'':
        #     raise ClientDisconnect('Client disconnected while receiving message')
        # return data

    # def recv_frame(self):
    #     frame = Frame().recv_frame(self.recv)
    #     self._handle_frame(frame)
    #     return frame

    # def _handle_frame(self, frame):
    #     if frame.fin == 0:
    #         logging.debug('A frame that is not the final frame was received')
    #         if frame.opcode != OpCode.CONTINUATION:
    #             self.unfinished_frame = frame
    #         else:
    #             self._continuation_frame(frame)
    #     else:
    #
    #         if frame.opcode == OpCode.CONTINUATION:
    #             self._continuation_frame(frame)
    #
    #             if self.unfinished_frame.opcode != OpCode.CONTINUATION:
    #                 self._handle_frame(self.unfinished_frame)
    #             self.unfinished_frame = None
    #
    #         elif frame.opcode == OpCode.CLOSE:
    #             print(frame.payload)
    #             logging.debug(
    #                 '{}: Close frame recd {} ({}) {}'.format(
    #                     self.address, StatusCode.get_int(frame.payload[0:2]),
    #                     StatusCode.status_codes[frame.payload[0:2]], frame.payload[2:].decode('utf-8'))
    #             )
    #             self.close_frame_recd = True
    #             self.close_lock.set()
    #             self.close(status_code=frame.payload)
    #
    #         elif frame.opcode == OpCode.PING:
    #             pong_frame = Frame(opcode=OpCode.PONG,
    #                                payload=frame.payload)
    #             self.send_frame(pong_frame, 10)
    #
    # def _continuation_frame(self, frame):
    #     if self.unfinished_frame is not None:
    #         self.unfinished_frame.payload += frame.payload
    #     else:
    #         logging.warning('{}: A continuation frame was received without getting the first frame.'.format(self.address))

    def close(self, status_code=StatusCode.NORMAL_CLOSE, reason='', timeout=2):
        if type(reason) == str:
            reason = reason.encode()
        self.state = Client.CLOSING
        if not self.close_frame_sent:
            frame = Frame(opcode=OpCode.CLOSE,
                          payload=status_code + reason)

            self.send(frame.pack())
            self.close_frame_sent = True

            logging.debug('{}: Close frame sent {} ({}) {}'.format(
                self.address, StatusCode.get_int(status_code),
                StatusCode.status_codes[status_code], reason
            ))

        self.close_lock.wait(timeout=timeout)
        self.close_lock.clear()

        # logging.debug('Closing connection: {}'.format(self.address))
        # self.socket.shutdown(socket.SHUT_RDWR)
        # self.socket.close()
        self.socket.close(reason)
        self.state = Client.CLOSED

    def get_state(self):
        return self._states[self.state]



