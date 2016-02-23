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
    client.send(frame.pack())
    return True


def handle_new_connection(client):
    print('Client connected')
    return True

server = ewebsockets.Websocket(
    handle_new_connection=handle_new_connection,
    handle_websocket_frame=handle_websocket_frame,
    esockets_kwargs={'max_subthreads': 10}
)


server.start()
print(server.server.host + ':' + str(server.server.port))
client = create_connection('ws://' + server.server.host + ':' + str(server.server.port))
client.send('hello\n', 1)

