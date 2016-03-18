#!/bin/env python3
import ewebsockets
import esockets
import logging, sys
from websocket import create_connection

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

#
# def handle_frame_payload(client, frame):
#     # frame.mask = 0
#     # print(client.address, ': ', frame.payload, ' Opcode: ', ewebsockets.OpCode.opcodes[frame.opcode])
#     # frame.payload = b'SERVER: ' + frame.payload
#     # if frame.opcode == ewebsockets.OpCode.TEXT:
#     #     for i in server.clients_list():
#     #         i.send_frame(frame)
#     # return True
#     print('LENGTH', frame.payload_length)
#     payload = frame.recv_payload(frame.payload_length)
#
#     print(client.address(), ': ', frame.payload)
#
#
# def handle_new_connection(client):
#     print('Client connected')
#     return True
#
# def on_client_open(client):
#     print('Client now in open state')
#
# def on_client_closed(client):
#     print('Client now in closing state')

class MyWsClientHandler(ewebsockets.WsClientHandler):
    def on_open(self):
        print(self.address, ': Now in open state')

    def on_message(self, frame, is_binary=False):
        frame.recv_payload(4096)
        print(self.address, frame.payload)
        self.send_text(b'SERVER: ' + frame.payload)

    def on_close(self, normal, code, info):
        if normal:
            print('Normal close:', code, info)
        else:
            print('Abnormal close:', '>', info, '<')

# server = ewebsockets.Websocket(
#     handle_new_connection=handle_new_connection,
#     handle_frame_payload=handle_frame_payload,
#     on_client_open=on_client_open,
#     on_client_closed=on_client_closed
# )

server = esockets.SocketServer(client_handler=MyWsClientHandler)
server.start()

print(server.host + ':' + str(server.port))
client = create_connection('ws://' + server.host + ':' + str(server.port))
client.send('hello\n', 1)

