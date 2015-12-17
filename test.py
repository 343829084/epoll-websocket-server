#!/bin/env python3
import EWebsocketS
import EWebsocketS.RFC6455 as RFC6455


class ws(EWebsocketS.Websocket):

    def on_connect(self, fileno):
        print(self.clients[fileno].getip(), 'Connected')

    def on_client_open(self, fileno):
        print(self.clients[fileno].getip(), 'Now in open state')

    def on_start(self):
        print('Started on: ', self.host, self.port)
        
    def on_normal_disconnect(self, fileno, reason):
        print('Closed connection: ', reason)
        del self.clients[fileno]

    def _on_abnormal_disconnect(self, fileno, msg):
        print('Abnormal disconnect ', reason)

    def on_text_recv(self, fileno, text):
        frame = RFC6455.WSframe(opcode=RFC6455.OC.TEXT,
                                payload=text)
        frame.pack()
        self.send(fileno, frame.frame)
        print(text)
        
s = ws()
s.start()

