#!/bin/env python3

from threading import Lock, Event
from .exceptions import *
from .RFC6455 import *
import logging
from json import JSONEncoder
# from esockets import ConnectionBroken
import esockets
import socket

class WsClientHandler(esockets.ClientHandler):
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3
    _states = {CONNECTING: 'Connecting',
               OPEN: 'Open',
               CLOSING: 'Closing',
               CLOSED: 'Closed'}

    def __init__(self):
        super(WsClientHandler, self).__init__()
        # esockets.Client.__init__(esockets.ClientHandler)
        self.state = self.CONNECTING

        self.close_event = Event()
        self.close_frame_sent = False
        self.handshake_timeout = 5

    def on_open(self):
        """Return True: the client is registered to the selector object
         Return False: the client is disconnected with protocol error and reason=Return value
        """
        pass

    def on_close(self, normal, code, info):
        pass

    def on_message(self, frame, is_binary):
        """User is expected to receive the whole payload (length in frame.payload_length
         recv data using data = frame.recv_payload
         Return True: the client is once again registered to the selector object
         Return False: the client is disconnected with protocol error and reason=Return value
        """
        frame.recv_payload(frame.payload_left)

    def send_text(self, text):
        if type(text) is str:
            text = text.encode()

        frame = Frame(opcode=OpCode.TEXT,
                      payload=text)

        self.send(frame.pack())

    def handle_socket_accept(self):
        """Wait for client to send a handshake
        """
        # Temporarily making the socket semi-blocking
        self.socket.settimeout(self.handshake_timeout)

        # Waiting for client to send handshake
        try:
            handshake = self.recv(4096)
        except socket.timeout:
            return StatusCode.PROTOCOL_ERROR + b'Timed out while waiting for handshake'
        finally:
            self.socket.settimeout(0)

        response = pack_handshake(handshake)
        if response is None:
            return StatusCode.PROTOCOL_ERROR + b'Invalid handshake'
        self.send(response)
        self.state = self.OPEN
        self.on_open()
        return True

    def handle_socket_message(self):
        """Handles websocket frames
        """
        # print(self.recv(2000))
        frame = Frame(client=self)  # will use client.recv to read frame

        try:
            is_valid = frame.recv_header()
            if is_valid is not None:
                return StatusCode.PROTOCOL_ERROR + is_valid

            is_valid = frame.recv_length()
            if is_valid is not None:
                return StatusCode.PROTOCOL_ERROR + is_valid

            if frame.opcode == OpCode.TEXT:
                return self.on_message(frame, is_binary=False)
            elif frame.opcode == OpCode.BINARY:
                return self.on_message(frame, is_binary=True)
            elif frame.opcode == OpCode.CLOSE:
                self.close_event.set()
                close_info = frame.recv_payload(min(frame.payload_left, 256))
                logging.debug('{}: Close frame received ( {} {})'.format(
                    self.address, bytes2int(close_info[:2]), close_info[2:]
                ))
                return close_info
            elif frame.opcode == OpCode.PING:
                if frame.payload_length > 256:
                    return StatusCode.PROTOCOL_ERROR + b'Ping payload too large'

                frame.recv_payload(frame.payload_left)
                pong_frame = Frame(opcode=OpCode.PONG,
                                   payload=frame.payload)
                self.send(pong_frame.pack())
            else:
                return StatusCode.PROTOCOL_ERROR + b'Opcode: ' + frame.opcode + b' not supported'
        except BlockingIOError:
            return StatusCode.PROTOCOL_ERROR + b'Invalid frame'


        return True

    def handle_socket_close(self, reason):
        """This function expects that a close frame was received
         otherwise calls on_close with normal=False
        """
        if type(reason) == bytes and not self.close_frame_sent:
            try:
                self.send_close(reason[:2], reason[2:])
                logging.debug('{}: Close frame sent'.format(self.address))
            except:
                logging.error('{}: Failed to send close frame'.format(self.address))
                pass

        if self.close_frame_sent and self.close_event.isSet():
            self.on_close(True, bytes2int(reason[:2]), reason[2:].decode('utf-8'))
        else:
            self.on_close(False, -1, reason)

    def send_close(self, code=StatusCode.NORMAL_CLOSE, reason=b''):
        close_frame = Frame(opcode=OpCode.CLOSE,
                            payload=code + reason)
        self.send(close_frame.pack())
        self.close_frame_sent = True

    def manual_close(self, code=StatusCode.NORMAL_CLOSE, reason='', timeout=2):
        try:
            self.send_close(code, reason.encode())
            self.close_event.wait(timeout)
        except:
            logging.error('Manual close failed to do a normal close')
            raise
        finally:
            if not self.socket_closed:
                self.close(reason)

        # return True
    #     if self.state == Client.CONNECTING:
    #         if self.do_handshake():
    #             return True
    #         else:
    #             return 'Invalid handshake'
    #
    #     elif self.state in (Client.OPEN, Client.CLOSING):
    #         frame = Frame(client=self)
    #         frame.recv_header()
    #         if frame.opcode not in OpCode.opcodes:
    #             # Invalid opcode recd
    #             self.close(StatusCode.PROTOCOL_ERROR + b'Invalid opcode')
    #             return
    #
    #         frame.recv_length()
    #
    #         if frame.opcode == OpCode.TEXT:
    #             self.handle_text_payload(frame)
    #         elif frame.opcode == OpCode.BINARY:
    #             self.handle_binary_payload(frame)
    #         elif frame.opcode == OpCode.PING:
    #             if frame.payload_length < 256:
    #                 frame.recv_payload(frame.payload_length)
    #                 pong_frame = Frame(opcode=OpCode.PONG,
    #                                    payload=frame.payload)
    #                 self.send(pong_frame.pack(), 2)
    #             else:
    #                 self.close(StatusCode.PROTOCOL_ERROR + b'Ping payload too large')
    #                 return






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

    #
    # def do_handshake(self):
    #     """
    #     :return:True/False (Success/Failed handshake)
    #     """
    #     client_handshake = self.recv(4096, fixed=False)
    #     logging.debug('{}: Received handshake'.format(self.address()))
    #     try:
    #         response = pack_handshake(client_handshake)
    #     except DataMissing:
    #         logging.warning('{}: Received unaccepted handshake'.format(self.address()))
    #         self.close(b'Protocol error')
    #         # self.socket.close('Received unaccepted handshake')  # just close the socket
    #         # because the handshake was not complete no RFC6455 protocol needs to be followed here
    #     else:
    #         self.socket.send(response, timeout=5)
    #         # if total_sent == len(response):
    #         self.state = self.OPEN
    #         self.on_open()
    #         logging.debug('{}: Handshake complete, client now in open state'.format(self.address()))
    #         # return True
    #         # else:
    #         #     logging.warning('{}: Handshake failed, {}/{} bytes of the response sent'.format(self.address(),
    #         #                                                                                     total_sent,
            #                                                                                     len(response)))
            #     return False

    # def send(self, bytes, timeout=-1):
    #     return self.socket.send(bytes, timeout)
    #
    # # def send_frame(self, frame, timeout=-1):
    # #     return self.send(frame.pack(), timeout)
    #
    # def send_text(self, text, timeout=-1, mask=0):
    #     if type(text) == str:
    #         frame = Frame(payload=text.encode(),
    #                       opcode=OpCode.TEXT,
    #                       mask=mask)
    #     else:
    #         frame = Frame(payload=text,
    #                       opcode=OpCode.TEXT,
    #                       mask=mask)
    #     return self.send(frame.pack(), timeout)
    #
    # def send_binary(self, bytes, timeout=-1, mask=0):
    #     frame = Frame(payload=bytes,
    #                   opcode=OpCode.BINARY,
    #                   mask=mask)
    #     self.send_frame(frame, timeout)

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

    # def recv(self, size, fixed=True):
    #     return self.socket.recv(size, fixed)
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

    # def close(self, status_code=StatusCode.NORMAL_CLOSE, reason='', timeout=2):
    #     if type(reason) == str:
    #         reason = reason.encode()
    #     self.state = Client.CLOSING
    #     if not self.close_frame_sent:
    #         frame = Frame(opcode=OpCode.CLOSE,
    #                       payload=status_code + reason)
    #
    #         self.send(frame.pack())
    #         self.close_frame_sent = True
    #
    #         logging.debug('{}: Close frame sent {} ({}) {}'.format(
    #             self.address, StatusCode.get_int(status_code),
    #             StatusCode.status_codes[status_code], reason
    #         ))
    #
    #     self.close_lock.wait(timeout=timeout)
    #     self.close_lock.clear()
    #
    #     # logging.debug('Closing connection: {}'.format(self.address))
    #     # self.socket.shutdown(socket.SHUT_RDWR)
    #     # self.socket.close()
    #     self.socket.close(reason)
    #     self.state = Client.CLOSED
    #
    # def get_state(self):
    #     return self._states[self.state]



