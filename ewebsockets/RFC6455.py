#!/bin/env python3
from random import randint
import base64, hashlib
from .bytes_convert import *
from .exceptions import *


def masking_algorithm(data, key):
    length = len(data)
    result = bytearray(length)
    for i in range(length):
        result[i] = data[i] ^ key[i % 4]
    return bytes(result)


#opcodes
class OpCode:
    CONTINUATION = b'\x00'
    TEXT = b'\x01'
    BINARY = b'\x02'
    RESERVED_NON_CONTROL_1 = b'\x02'
    RESERVED_NON_CONTROL_2 = b'\x03'
    RESERVED_NON_CONTROL_3 = b'\x04'
    RESERVED_NON_CONTROL_4 = b'\x05'
    RESERVED_NON_CONTROL_5 = b'\x06'
    RESERVED_NON_CONTROL_6 = b'\x07'
    CLOSE = b'\x08'
    PING = b'\x09'
    PONG = b'\x0A'
    RESERVED_CONTROL_1 = b'\x0B'
    RESERVED_CONTROL_2 = b'\x0C'
    RESERVED_CONTROL_3 = b'\x0D'
    RESERVED_CONTROL_4 = b'\x0E'
    RESERVED_CONTROL_5 = b'\x0F'

    opcodes = {CONTINUATION: 'continuation',
               TEXT: 'text',
               BINARY: 'binary',
               RESERVED_NON_CONTROL_1: 'reserved non control 1',
               RESERVED_NON_CONTROL_2: 'reserved non control 2',
               RESERVED_NON_CONTROL_3: 'reserved non control 3',
               RESERVED_NON_CONTROL_4: 'reserved non control 4',
               RESERVED_NON_CONTROL_5: 'reserved non control 5',
               RESERVED_NON_CONTROL_6: 'reserved non control 6',
               CLOSE: 'close',
               PING: 'ping',
               PONG: 'pong',
               RESERVED_CONTROL_1: 'reserved control 1',
               RESERVED_CONTROL_2: 'reserved control 2',
               RESERVED_CONTROL_3: 'reserved control 3',
               RESERVED_CONTROL_4: 'reserved control 4',
               RESERVED_CONTROL_5: 'reserved control 5'}

    @staticmethod
    def is_valid(opcode):
        if type(opcode) == int:
            opcode = int2bytes(opcode, 1)

        if opcode in OpCode.opcodes.keys():
            return True
        else:
            return False


#statuscodes
class StatusCode:
    NORMAL_CLOSE = b'\x03\xE8'  # Status code 1000
    ENDP_GOING_AWAY = b'\x03\xE9'  # Status code 1001
    PROTOCOL_ERROR = b'\x03\xEA'  # Status code 1002
    DATA_ACCEPT_ERROR = b'\x03\xEB'  # Status code 1003
    RESERVED_STATUS_CODE_1004 = b'\x03\xEC'  # Status code 1004
    RESERVED_STATUS_CODE_1005 = b'\x03\xED'  # Status code 1005
    RESERVED_STATUS_CODE_1006 = b'\x03\xEE'  # Status code 1006
    DATA_TYPE_ERROR = b'\x03\xEF'  # Status code 1007
    POLICY_VIOLATION = b'\x03\xF0'  # Status code 1008
    MESSAGE_TOO_BIG = b'\x03\xF1'  # Status code 1009
    CLIENT_EXTENSION_ERROR = b'\x03\xF2'  # Status code 1010
    UNEXPECTED_CONDITION = b'\x03\xF3'  # Status code 1011
    TLS_HANDSHAKE_ERROR = b'\x03\xF7'  # Status code 1015

    status_codes = {NORMAL_CLOSE: 'Normal close',
                    ENDP_GOING_AWAY: 'Endpoint going away',
                    PROTOCOL_ERROR: 'Protocol error',
                    DATA_ACCEPT_ERROR: 'Data accept error',
                    RESERVED_STATUS_CODE_1004: 'Reserved status code',
                    RESERVED_STATUS_CODE_1005: 'Reserved status code',
                    RESERVED_STATUS_CODE_1006: 'Reserved status code',
                    DATA_TYPE_ERROR: 'Data type error',
                    POLICY_VIOLATION: 'Policy violation',
                    MESSAGE_TOO_BIG: 'Message too big',
                    CLIENT_EXTENSION_ERROR: 'Client extension error',
                    UNEXPECTED_CONDITION: 'Unexpected condition',
                    TLS_HANDSHAKE_ERROR: 'TLS handshake error'}

    @staticmethod
    def is_valid(status_code):
        if type(status_code) == int:
            status_code = int2bytes(status_code, 2)

        if status_code in StatusCode.status_codes:
            return True
        else:
            return False

    @staticmethod
    def get_int(status_code):
        return int(status_code.hex(), 16)

class Frame:
    def __init__(self, fin=1, rsv=(0,0,0), opcode=None, mask=0,
                 payload=None, client=None):
        self.fin = fin
        self.rsv = rsv
        self.opcode = opcode
        self.mask = mask
        self.payload = payload
        self.client = client

        self.payload_length = None
        self.masking_key = None

        self.payload_recd = 0
        self.header_recd = False
        self.length_recd = False

    def pack(self):

        frame_head = bytearray(2)
        frame_head[0] = self.fin << 7
        frame_head[0] |= self.rsv[0] << 6
        frame_head[0] |= self.rsv[1] << 5
        frame_head[0] |= self.rsv[2] << 4
        frame_head[0] |= bytes2int(self.opcode)

        frame_head[1] = self.mask << 7

        payload_length = len(self.payload)
        if payload_length < 126:
            payload_length_ext = bytearray(0)
            frame_head[1] |= payload_length
        elif payload_length < 65536:
            payload_length_ext = int2bytes(payload_length, 2)
            frame_head[1] |= 126
        elif payload_length < 18446744073709551616:
            payload_length_ext = int2bytes(payload_length, 8)
            frame_head[1] |= 127
        else:
            raise InvalidFrame('Payload too large')

        payload = self.payload
        if self.mask:
            self.get_masking_key()
            payload = masking_algorithm(self.payload, self.masking_key)

        return bytes(frame_head + payload_length_ext + (self.masking_key or bytearray(0)) + payload)

        # return bytes(frame_head + payload_length_ext + self.payload)

    # def unmask_payload(self):
    #     self.payload = masking_algorithm(self.payload_masked, self.masking_key)
    #     return self.payload
    #
    # def update_masking(self, new_key=True):
    #     if new_key:
    #         self.masking_key = int2bytes(randint(0, 2**32-1), 4)
    #     self.payload_masked = masking_algorithm(self.payload, self.masking_key)

    def get_masking_key(self):
        self.masking_key = int2bytes(randint(0, 2**32-1), 4)
        return self.masking_key

    def recv_header(self):
        """Receives the header and payload length
        """
        header = self.client.recv(1)
        self.fin = header[0] >> 7
        self.rsv = (header[0] >> 6 & 0b00000001,
                    header[0] >> 5 & 0b00000001,
                    header[0] >> 4 & 0b00000001)
        self.opcode = bytes(int2bytes(header[0] & 0b00001111, 1))
        self.header_recd = True

    def recv_length(self):
        if not self.header_recd:
            self.recv_header()

        header2 = self.client.recv(1)
        self.mask = header2[0] >> 7
        self.payload_length = header2[0] & 0b01111111

        if self.payload_length == 126:
            self.payload_length = bytes2int(self.client.recv(2))
        elif self.payload_length == 127:
            self.payload_length = bytes2int(self.client.recv(8))
        else:
            self.payload_length = self.payload_length

        self.length_recd = True

    def recv_payload(self, size):
        if not self.length_recd:
            self.recv_length()
        if size > self.payload_length - self.payload_recd:
            raise ValueError('Tried receiving more payload than the payload length')

        if self.mask and self.masking_key is None:
            self.masking_key = self.client.recv(4)

        data = self.client.recv(size)
        recd = len(data)

        if self.mask:
            result = bytearray(recd)
            for i in range(self.payload_recd, self.payload_recd + recd):
                result[i - self.payload_recd] = data[i - self.payload_recd] ^ self.masking_key[i % 4]
            data = bytes(result)

        self.payload_recd += recd
        if self.payload is None:
            self.payload = data
        else:
            self.payload += data

        return data

    # def recv_frame(self, recv_function):
        # header = recv_function(2)
        #
        # self.fin = header[0] >> 7
        # self.rsv = (header[0] >> 6 & 0b00000001,
        #             header[0] >> 5 & 0b00000001,
        #             header[0] >> 4 & 0b00000001)
        # self.opcode = bytes(int2bytes(header[0] & 0b00001111, 1))
        # self.mask = header[1] >> 7
        # self.payload_length = header[1] & 0b01111111
        #
        # if self.payload_length == 126:
        #     payload_length = bytes2int(recv_function(2))
        # elif self.payload_length == 127:
        #     payload_length = bytes2int(recv_function(8))
        # else:
        #     payload_length = self.payload_length
        #
        #
        # if self.mask:
        #     self.masking_key = recv_function(4)
        #     self.payload_masked = recv_function(self.payload_length)
        #     self.unmask_payload()
        # else:
        #     self.payload = recv_function(self.payload_len)
        #
        # return self


guid = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def pack_handshake(client_handshake):
    key = None
    for line in client_handshake.splitlines():
        if b'Sec-WebSocket-Key:' in line:
            key = line.split(b': ')[1]
    if key is None:
        raise DataMissing('Did not find websocket key in handshake')

    handshake = b'HTTP/1.1 101 Switching Protocols\r\n'
    handshake += b'Upgrade: websocket\r\n'
    handshake += b'Connection: Upgrade\r\n'
    handshake += b'Sec-WebSocket-Accept: '
    handshake += base64.b64encode(hashlib.sha1(key+guid).digest())
    handshake += b'\r\n\r\n'
    return handshake


def read_frame_head(frame_head):
    frame = Frame(
        fin=frame_head[0] >> 7,
        rsv=(frame_head[0] >> 6 & 0b00000001,
             frame_head[0] >> 5 & 0b00000001,
             frame_head[0] >> 4 & 0b00000001),
        opcode=bytes(int2bytes(frame_head[0] & 0b00001111, 1)),
        mask=frame_head[1] >> 7,
        payload_length=frame_head[1] & 0b01111111
    )
    # frame.fin = frame_head[0] >> 7
    # frame.rsv = (frame_head[0] >> 6 & 0b00000001,
    #              frame_head[0] >> 5 & 0b00000001,
    #              frame_head[0] >> 4 & 0b00000001)
    #
    # frame.opcode = bytes(int2bytes(frame_head[0] & 0b00001111, 1))

    if not OpCode.is_valid(frame.opcode):
        raise FrameError('Opcode: {} is not recognized'.format(frame.opcode))

    # frame.mask = frame_head[1] >> 7
    # frame.payload_length = frame_head[1] & 0b01111111
    return frame
