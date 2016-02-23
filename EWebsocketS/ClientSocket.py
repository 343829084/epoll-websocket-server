#!/bin/env python3

from threading import Lock, Condition
from EWebsocketS.exceptions import *
from EWebsocketS.RFC6455 import *
import logging
import socket

class Client:
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3

    def __init__(self, socket, address, state=0):
        self.socket = socket
        self.state = state
        self.address = address
        self.close_frame_sent = False
        self.close_frame_recv = False
        self.send_lock = Lock()
        self.close_lock = Condition()
        self.unfinished_frame = None

    def send(self, msg, timeout=-1):
        total_sent = 0
        if self.send_lock.acquire(timeout=timeout):
            try:
                msg_len = len(msg)
                while total_sent < msg_len:
                    sent = self.socket.send(msg[total_sent:])
                    if sent == 0:
                        raise ClientDisconnect("Socket connection broken")
                    total_sent = total_sent + sent
            finally:
                self.send_lock.release()
        return total_sent

    def recv_all(self, size, chunk_size=2048):
        data = bytearray(size)
        bytes_recd = 0

        while bytes_recd < size:
            to_recv = min(size-bytes_recd, chunk_size)
            try:
                chunk = self.recv(to_recv)
            except BlockingIOError:
                raise DataMissing('Expected to receive {} bytes but '
                                  'only found {} bytes in the buffer'.format(size, bytes_recd))
            else:
                if len(chunk) != to_recv:
                    raise DataMissing('Expected to receive {} bytes but '
                                      'only found {} bytes in the buffer'.format(size, bytes_recd))

                data[bytes_recd:bytes_recd+to_recv] = chunk
                bytes_recd += len(chunk)
        return data

    def recv(self, size):
        data = self.socket.recv(size)
        if data == b'':
            raise ClientDisconnect('Client disconnected while receiving message')
        return data

    def recv_frame(self):
        frame_head = self.recv_all(2)
        frame = read_frame_head(frame_head)
        if frame.payload_len == 126:
            payload_len = bytes2int(self.recv_all(2))
        elif frame.payload_len == 127:
            payload_len = bytes2int(self.recv_all(8))
        else:
            payload_len = frame.payload_len

        if frame.mask:
            frame.masking_key = self.recv_all(4)
            frame.payload_masked = self.recv_all(payload_len)
            frame.unmask_payload()
        else:
            frame.payload = self.recv_all(payload_len)

        self._handle_frame(frame)
        return frame

    def _handle_frame(self, frame):
        if frame.fin == 0:
            logging.debug('A frame that is not the final frame was received')
            if frame.opcode != OpCode.CONTINUATION:
                self.unfinished_frame = frame
            else:
                self._continuation_frame(frame)
            return -1
        else:

            if frame.opcode == OpCode.CONTINUATION:
                self._continuation_frame(frame)

                if self.unfinished_frame.opcode != OpCode.CONTINUATION:
                    self._handle_frame(self.unfinished_frame)
                self.unfinished_frame = None

            elif frame.opcode == OpCode.CLOSE:
                self.close_frame_recv = True
                if self.close_frame_sent:
                    with self.close_lock:
                        self.close_lock.notify_all()
                else:
                    self.close()
            elif frame.opcode == OpCode.PING:
                pong_frame = Frame(opcode=OpCode.PONG,
                                   payload=frame.payload).pack()
                self.send(pong_frame, 10)

    def _continuation_frame(self, frame):
        if self.unfinished_frame is not None:
            self.unfinished_frame.payload += frame.payload
        else:
            logging.warning('{}: A continuation frame was received without getting the first frame.'.format(self.address))

    def close(self, status_code=StatusCode.NORMAL_CLOSE, timeout=10):
        if not self.close_frame_sent:
            frame = Frame(opcode=OpCode.CLOSE,
                          payload=status_code)
            self.send(frame)
            self.close_frame_sent = True
            self.state = self.CLOSING

        if not self.close_frame_recv:
            self.state = self.CLOSING
            with self.close_lock:
                self.close_lock.wait(timeout=timeout)

        # logging.debug('Closing connection: {}'.format(self.address))
        # self.socket.shutdown(socket.SHUT_RDWR)
        # self.socket.close()
        self.state = self.CLOSED





