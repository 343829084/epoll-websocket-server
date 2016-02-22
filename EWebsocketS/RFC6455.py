#!/bin/env python3
from random import randint
import base64, hashlib
from .bytes_convert import *
from .exceptions import *

GUID = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def masking_algorithm(data, key):
    length = len(data)
    result = bytearray(length)
    for i in range(length):
        result[i] = data[i] ^ key[i % 4]
    return bytes(result)


#opcodes
class OC:
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

        if opcode in OC.opcodes.keys():
            return True
        else:
            return False


#statuscodes
class SC:
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

        if status_code in SC.status_codes:
            return True
        else:
            return False


class Frame:
    def __init__(self, FIN, RSV, opcode, mask, payload, masking_key=None):
        self.FIN = FIN
        self.RSV = RSV
        self.opcode = opcode
        self.mask = mask
        self.masking_key = masking_key
        self.payload = payload

    def pack(self):

        frame_head = bytearray(2)
        frame_head[0] = self.FIN << 7
        frame_head[0] |= self.RSV[0] << 6
        frame_head[0] |= self.RSV[1] << 5
        frame_head[0] |= self.RSV[2] << 4
        frame_head[0] |= bytes2int(self.opcode)

        frame_head[1] = self.mask << 7

        payload_len = len(self.payload)
        if payload_len < 126:
            payload_ext = bytearray(0)
            frame_head[1] |= payload_len
        elif payload_len < 65536:
            payload_ext = int2bytes(payload_len, 2)
            frame_head[1] |= 126
        elif payload_len < 18446744073709551616:
            payload_ext = int2bytes(payload_len, 8)
            frame_head[1] |= 127
        else:
            raise InvalidFrame('Payload too large')

        if self.mask:
            masking_key = int2bytes(randint(0, 2**32-1), 4)
            payload = masking_algorithm(self.payload, masking_key)
        else:
            masking_key = bytearray(0)
            payload = self.payload

        return bytes(frame_head + payload_ext + masking_key + payload)


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
    handshake += base64.b64encode(hashlib.sha1(key+GUID).digest())
    handshake += b'\r\n\r\n'
    return handshake


