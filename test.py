#!/bin/env python3
import EWebsocketS
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
    print('Client: ', frame.unmask_payload(),  EWebsocketS.OpCode.opcodes[frame.opcode])
    client.send(frame.pack())
    return True


def handle_new_connection(client, address):
    print('Client connected')
    return True

server = EWebsocketS.Websocket(
    handle_new_connection=handle_new_connection,
    handle_websocket_frame=handle_websocket_frame,
    esockets_kwargs={'max_subthreads': 10}
)

server.start()
print(server.server.host + ':' + str(server.server.port))
client = create_connection('ws://' + server.server.host + ':' + str(server.server.port))
client.send('hello\n', 10)