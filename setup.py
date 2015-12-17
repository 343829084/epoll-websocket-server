#!/bin/env python3
from distutils.core import setup
#from setuptools import setup
setup(
  name = 'EWebsocketS',
  packages = ['EWebsocketS'], # this must be the same as the name above
  version = '0.0.1',
  license = 'MIT',
  description = 'A websocket server based on ESocketS and the 6455 websocket protocol',
  author = 'Christoffer Zakrisson',
  author_email = 'christoffer_zakrisson@hotmail.com',
  url = 'https://github.com/Zaeb0s/epoll-websocket-server', # use the URL to the github repo
  keywords = ['websocket', 'socket', 'epoll', 'server', 'poll', 'select', 'TCP', 'web'], # arbitrary keywords
  classifiers = ['Development Status :: 3 - Alpha',
                 'Programming Language :: Python :: 3.5',
                 'Operating System :: POSIX :: Linux',
                 'License :: OSI Approved :: MIT License'],
)
