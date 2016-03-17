#!/bin/env python3
import ewebsockets
import logging, sys
from websocket import create_connection

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)


def handle_frame_payload(client, frame):
    # frame.mask = 0
    # print(client.address, ': ', frame.payload, ' Opcode: ', ewebsockets.OpCode.opcodes[frame.opcode])
    # frame.payload = b'SERVER: ' + frame.payload
    # if frame.opcode == ewebsockets.OpCode.TEXT:
    #     for i in server.clients_list():
    #         i.send_frame(frame)
    # return True
    print('LENGTH', frame.payload_length)
    payload = frame.recv_payload(frame.payload_length)

    print(client.address(), ': ', frame.payload)


def handle_new_connection(client):
    print('Client connected')
    return True

def on_client_open(client):
    print('Client now in open state')

def on_client_closed(client):
    print('Client now in closing state')

server = ewebsockets.Websocket(
    handle_new_connection=handle_new_connection,
    handle_frame_payload=handle_frame_payload,
    on_client_open=on_client_open,
    on_client_closed=on_client_closed
)


server.start()
print(server.server.host + ':' + str(server.server.port))
client = create_connection('ws://' + server.server.host + ':' + str(server.server.port))
client.send('hello\n', 1)

