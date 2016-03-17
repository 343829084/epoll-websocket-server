#!/bin/env python3

import esockets
import logging
from .RFC6455 import *
from .ClientSocket import Client


class Websocket:
    def __init__(self,
                 handle_new_connection=lambda client: True,
                 handle_frame_payload=lambda client, frame: True,
                 on_client_open=lambda client: True,
                 on_client_closed=lambda client: True,
                 esockets_kwargs={}):

        self.handle_new_connection = handle_new_connection
        self.handle_frame_payload = handle_frame_payload
        self.on_client_open = on_client_open
        self.on_client_closed = on_client_closed

        kwargs = dict(esockets_kwargs)
        kwargs.update({'handle_incoming': self._handle_incoming})
        kwargs.update({'handle_readable': self._handle_readable})
        kwargs.update({'handle_closed': self._handle_closed})
        self.server = esockets.SocketServer(**kwargs)

        self.clients = {}

    def _handle_incoming(self, sock):
        """The esockets required function for handling incoming client connections
        """
        client = Client(sock,
                        on_open=self.on_client_open)
        self.clients[sock] = client
        self.handle_new_connection(client)

        # if self.handle_new_connection(client):
        #     self.clients.append(client)
        #     return True
        # return False

    def _handle_closed(self, sock, reason):
        client = self.clients[sock]
        del self.clients[sock]
        self.on_client_closed(client)

    def _handle_readable(self, sock):
        """The esockets required function for handling incoming data from clients
        """
        client_obj = self.clients[sock]
        if client_obj.state == Client.CONNECTING:
            # handshake_success = client_obj.do_handshake()
            # if handshake_success:
            #     self.on_client_open(client_obj)
            # return handshake_success
            client_obj.do_handshake()
        elif client_obj.state == Client.OPEN or client_obj.state == Client.CLOSING:
            frame = Frame(client=client_obj)
            frame.recv_header()

            # # frame = client_obj.recv_frame()
            if not OpCode.is_valid(frame.opcode):
                client_obj.close(staus_code=StatusCode.PROTOCOL_ERROR,
                                 reason='Invalid opcode')
                return
            frame.recv_length()

            if frame.opcode in (OpCode.TEXT, OpCode.BINARY, OpCode.CONTINUATION):

                if not self.handle_frame_payload(client_obj, frame):  # Returns false on invalid request
                    client_obj.close(status_code=StatusCode.PROTOCOL_ERROR,
                                     reason=b'Invalid request')
                    return
                elif frame.payload_length != frame.payload_recd:
                    # If entire payload was not read by handle_frame_payload
                    client_obj.close(status_code=StatusCode.PROTOCOL_ERROR,
                                     reason=b'Payload too large')
                    return
            else:
                frame.recv_payload(min(256, frame.payload_length))

                if frame.opcode == OpCode.CLOSE:
                    client_obj.close_lock.set()
                    client_obj.close(status_code=frame.payload[0:2],
                                     reason=frame.payload[2:])
                    return
                elif frame.opcode == OpCode.PING:
                    if frame.payload_length != frame.payload_recd:
                        client_obj.close(status_code=StatusCode.PROTOCOL_ERROR,
                                         reason=b'Ping payload too large')
                        return

                    response = Frame(payload=frame.payload,
                                     opcode=OpCode.PONG).pack()
                    client_obj.send(response)





            #     logging.info('{}: Closing connection, invalid opcode: {}'.format(client_obj.address, frame.opcode))
            #     return False
            #
            # if frame.fin == 1:
            #     # Let the user handle a finished frame
            #     if not self.handle_websocket_frame(client_obj, frame):
            #         # if handle_websocket_frame returns false send close frame and emedietely disconnect user
            #         logging.info('{}: Closing connection because handle_websocket_frame returned false'.format(client_obj.address))
            #         self.close_connection(sock)
            #         return False
            #
            # if frame.opcode == OpCode.CLOSE:

                # client_obj.close()
                # del self.clients[sock]
            #     return False
            # else:
            #     return True

    def start(self):
        self.server.start()

    def stop(self):
        # for client in self.clients_list():
        #     self.close_connection(client)
        #
        self.server.stop()

    # def clients_list(self):
    #     return list(self.clients.values())

    def close_connection(self, client, status_code=StatusCode.PROTOCOL_ERROR, reason=b''):
        try:
            client.close(status_code=status_code, timeout=0, reason=reason)
        finally:
            self.server.disconnect(client.socket)
            del self.clients[client.socket]

    def send_text(self, client, text, timeout=-1, mask=0):
        try:
            client.send_text(text, timeout, mask)
        except (OSError, BrokenPipeError, ClientDisconnect):
            self.close_connection(client, StatusCode.ENDP_GOING_AWAY, b'Broken pipe')
            logging.error('{}: Broken pipe'.format(client.address))

