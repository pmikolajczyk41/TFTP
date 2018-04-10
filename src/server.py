#!/usr/bin/env python3

import sys
import threading
import os
from common import *


class serverTFTP:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(timeout)

    def start(self, port=default_port, path=""):
        self.port = int(port)
        self.path = path
        try:
            self.sock.bind(('', self.port))
        except socket.error:
            print("invalid port")
            return

        self.monitor()

    def monitor(self):
        while True:
            request, client = receive(self.sock, None, None, None)
            if request == client is None: continue
            logging.debug("server received {} from {}".format(request, client))
            self.connection_handler(request, client, self.path).start()

    class connection_handler(threading.Thread):
        def __init__(self, request, client, path):
            super().__init__()

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.settimeout(timeout)
            self.sock.bind(('', 0))
            logging.debug(
                "server generates tid: {} for client {}, {}".format(self.sock.getsockname()[1], client[0], client[1]))

            self.path = path
            self.last_sent = None
            self.client = client
            self.request = request
            self.windowsize = 1
            self.history = {}
            self.last_sent_window = []

        def run(self):
            self.parse_request()
            print("\nserver: connection finished\n")

        def parse_request(self):
            # not RRQ
            if b2i(self.request[:2]) != 1:
                print("wrong opcode")
                return

            # obtain filename and windowsize
            strings = self.request[2:].split(b'\x00')
            self.filename = strings[0].decode()
            for opcode in range(len(strings)):
                if strings[opcode] == b'windowsize':
                    self.windowsize = int(strings[opcode + 1].decode())
                    break

            if self.windowsize > 1:
                self.last_sent = send_oack(self.sock, self.windowsize, self.client[0], self.client[1])

            while self.windowsize > 1:
                ack, sender = receive(self.sock, self.last_sent, self.client[0], self.client[1])
                if ack is None:
                    print("connection lost")
                    return
                elif sender != self.client or ack[:2] != i2b(4) or ack[2:4] != i2b(0):
                    continue
                else:
                    break
            self.read_request()

        def read_request(self):
            logging.debug("client wants to read {} with windowsize {}".format(self.filename, self.windowsize))
            last_acked = 0
            last_tried = 0
            eof = False
            with open(os.path.join(self.path, self.filename), "rb") as istream:
                while True:
                    self.last_sent_window = []
                    for i in range(self.windowsize):
                        to_be_sent = (last_acked + 1 + i) % 2 ** 16
                        data = istream.read(512) if to_be_sent not in self.history else self.history.get(to_be_sent)
                        self.history[to_be_sent] = data
                        if len(data) == 0 and eof: break  # EOF
                        if len(data) < 512: eof = True
                        send_data(self.sock, i2b(to_be_sent), data, self.client[0], self.client[1])
                        last_tried = to_be_sent
                        self.last_sent_window.append(i2b(3) + i2b(to_be_sent) + data)
                    if len(self.last_sent_window) == 0: break
                    while True:
                        ack, sender = receive(self.sock, self.last_sent_window, self.client[0], self.client[1])
                        if ack == sender is None:
                            print("connection lost")
                            return

                        # validate speaker
                        if self.client[1] != int(sender[1]) or self.client[0] != sender[0]: continue

                        # error
                        if check_error(ack): return

                        # not ack
                        if ack[:2] != i2b(4): continue

                        logging.debug("server received ack {} from {}".format(ack, sender))

                        # well done
                        if ack[2:4] == i2b(last_tried):
                            logging.debug("server's whole data window was ACKed (till block {})".format(last_tried))
                            self.history = {}
                            last_acked = last_tried
                            break

                        # part of the last window
                        if (last_acked < last_tried and b2i(ack[2:4]) in range(last_acked, last_tried)) or \
                                (b2i(ack[2:4]) > last_acked > last_tried) or (last_acked > last_tried > b2i(ack[2:4])):
                            logging.debug("server has to start new window from block {}".format(b2i(ack[2:4]) + 1))
                            while last_acked != b2i(ack[2:4]):
                                if last_acked in self.history: del self.history[last_acked]
                                last_acked = (last_acked + 1) % 2 ** 16
                            if last_acked in self.history: del self.history[last_acked]
                            break

                        # vagabond
                        else:
                            continue


#logging.basicConfig(level=logging.DEBUG)
server = serverTFTP()
if len(sys.argv) == 1:
    server.start()
elif len(sys.argv) == 2:
    server.start(sys.argv[1])
else:
    server.start(sys.argv[1], sys.argv[2])
