#!/bin/env python3
import ESocketS
import EWebsocketS.RFC6455 as RFC6455

class Connection(ESocketS.Connection):
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3

    def __init__(self, conn, address, recv_queue=False):
        ESocketS.Connection.__init__(self, conn, address, recv_queue)
        self.state = self.CONNECTING
        self.fragments = [b'', b'']
