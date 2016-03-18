#!/bin/env python3
# from .websocket_server import Websocket
from .RFC6455 import *
from .ClientSocket import *

with open(__path__[0] + '/version', 'r') as r:
    __version__ = r.read()
