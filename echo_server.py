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


def handle_websocket_frame(client, frame):
    frame.mask = 0
    print(client.address, ': ', frame.payload, ' Opcode: ', ewebsockets.OpCode.opcodes[frame.opcode])
    frame.payload = b'SERVER: ' + frame.payload
    if frame.opcode == ewebsockets.OpCode.TEXT:
        for i in server.clients_list():
            i.send_frame(frame)
    return True


def handle_new_connection(client):
    print('Client connected')
    return True

def on_client_open(client):
    print('Client now in open state')

def on_client_close(client):
    print('Client now in closing state')

server = ewebsockets.Websocket(
    handle_new_connection=handle_new_connection,
    handle_websocket_frame=handle_websocket_frame,
    on_client_open=on_client_open,
    on_client_close=on_client_close
)


server.start()
print(server.server.host + ':' + str(server.server.port))
client = create_connection('ws://' + server.server.host + ':' + str(server.server.port))
client.send('hello\n', 1)

