#!/bin/env python3
from random import randint
import base64, hashlib
from EWebsocketS.bytes_convert import bytes2int, int2bytes


GUID = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
def masking_algorithm(data, key):
    # data -- byte array
    # key -- byte array -- len(key)=4
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

    @staticmethod
    def genall():
        for key, value in OC.__dict__.items():
            if type(value) == bytes:
                yield value


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

    @staticmethod
    def genall():
        for key, value in SC.__dict__.items():
            if type(value) == bytes:
                yield value


class WSframe:
    def __init__(self, frame=None,
                 FIN=1,
                 RSV=[0, 0, 0],
                 opcode=None,
                 masking=0,
                 payload=None,
                 pre_test = True):

        self.FIN, self.RSV, self.opcode = FIN, RSV, opcode
        self.masking, self.payload = masking, payload
        self.frame = frame
        self.pre_test = pre_test
        self.rest = b''

    def pre_pack_check(self):
        if self.opcode not in OC.genall():
            return False, 'Opcode needs to be a recognized bytes object (use the opcodes provided in the RFC6455.OC class)'
        elif self.FIN not in [0, 1]:
            return False, 'FIN bit needs to be 0 or 1'
        elif type(self.RSV) != list or (type(self.RSV) == list and len(self.RSV) != 3):
            return False, 'RSV needs to be a list of length 3'
        elif self.RSV[0] not in [0, 1] or self.RSV[1] not in [0, 1] or self.RSV[2] not in [0, 1]:
            return False, 'Entrys in RSV needs to be either 1 or 0'
        elif self.masking not in [0, 1]:
            return False, 'Masking neeeds to be either 1 or 0'
        elif type(self.payload) != bytes:
            return False, 'Payload needs to be a bytes object'
        else:
            return True, ''

    def pre_unpack_check(self):
        if type(self.frame) != bytes:
            return False, 'The frame needs to be a bytes object'
        elif len(self.frame) < 3:
            return False, 'The websocket frame can not be smaller than two bytes'
        else:
            return True, ''

    def pack(self):
        if self.pre_test:
            passtest, message = self.pre_pack_check()
            if not passtest:
                raise RFC6455Error(message)

        payload_len = len(self.payload)
        if payload_len < 126:
            payload_ext = bytearray(0)
        elif payload_len < 65536:
            payload_ext = int2bytes(payload_len, 2)
            payload_len = 126
        elif payload_len < 18446744073709551616:
            payload_ext = int2bytes(payload_len, 8)
            payload_len = 127
        else:
            raise RFC6455Error('Payload too large')

        if self.masking:
            masking_key = int2bytes(randint(0, 2**32-1), 4)
            payload = masking_algorithm(self.payload, masking_key)
        else:
            masking_key = bytearray(0)

        frame_head = bytearray(2)
        frame_head[0] = (self.FIN << 7) | (self.RSV[0] << 6) | (self.RSV[1] << 5) | (self.RSV[2] << 4) | bytes2int(self.opcode)
        frame_head[1] = (self.masking << 7) | payload_len
        self.frame = bytes(frame_head + payload_ext + masking_key + self.payload)
        return self.frame

    def unpack(self):
        """
        Unpacks the websocket frame and returns
        FIN, [RSV1, RSV2, RSV3], opcode, payload, rest
        Where rest is any bytes that is not within the first websocket frame
        This makes it so that the user can iterate through a bytes string containing
        one or more websocket frames
        If data is missing from a frame an RFC6455Error exception will be thrown
        """
        try:
            frame = self.frame
            if self.pre_test:
                passtest, message = self.pre_unpack_check()
                if not passtest:
                    raise RFC6455Error(message)


            i = 0  # i is the number of interpreted frame bytes
            FIN = frame[i] >> 7
            RSV1 = frame[i] >> 6 & 0b00000001
            RSV2 = frame[i] >> 5 & 0b00000001
            RSV3 = frame[i] >> 4 & 0b00000001
            opcode = bytes(int2bytes(frame[i] & 0b00001111, 1))

            if opcode not in OC.genall():
                raise InvalidFrame('Opcode is not recognized')

            i += 1
            mask = frame[i] >> 7
            payload_len = frame[i] & 0b01111111

            i += 1
            if payload_len == 126:
                payload_len = bytes2int(frame[i:i+2])
                i += 2
            elif payload_len == 127:
                payload_len = bytes2int(frame[i:i+8])
                i += 8

            if mask:
                masking_key = frame[i:i+4]
                i += 4

            payload = frame[i:i+payload_len]
            i += payload_len

            frame[i-1]  # just to trigger error if frame to short

            if mask:
                payload = masking_algorithm(payload, masking_key)

            rest = frame[i:-1]

            self.FIN, self.RSV, self.opcode = FIN, [RSV1, RSV2, RSV3], opcode
            self.masking, self.payload = mask, payload
            self.rest = rest

            return payload_len, FIN, [RSV1, RSV2, RSV3], opcode, payload, rest
        except IndexError:
            raise InvalidFrame('Parts of the frame is missing')


def pack_handshake(client_handshake):
    key = None
    for line in client_handshake.splitlines():
        if b'Sec-WebSocket-Key:' in line:
            key = line.split(b': ')[1]
    if key is None:
        raise RFC6455Error('Did not find websocket key in handshake')

    handshake = b'HTTP/1.1 101 Switching Protocols\r\n'
    handshake += b'Upgrade: websocket\r\n'
    handshake += b'Connection: Upgrade\r\n'
    handshake += b'Sec-WebSocket-Accept: '
    handshake += base64.b64encode(hashlib.sha1(key+GUID).digest())
    handshake += b'\r\n\r\n'

    return handshake


class RFC6455Error(Exception):
    pass


class DataMissing(Exception):
    pass

class InvalidFrame(Exception):
    pass

if __name__ == '__main__':
    test_frame = WSframe(opcode=OC.PONG, payload='hello')
    print(test_frame)
    test_frame.pack()
    test_frame.unpack()
    print(test_frame.frame)
    print(test_frame)
    h = b'HTTP/1.1 101 Switching Protocols\r\n'
    h += b'Upgrade: websocket\r\n'
    h += b'Connection: Upgrade\r\n'
    h += b'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=='
    h += b'\r\n\r\n'

    print(pack_handshake(h))
