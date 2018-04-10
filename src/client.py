#!/usr/bin/env python3

import sys
import hashlib
from common import *


class clientTFTP:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mode = b'\x00octet\x00'
        self.server = None  # destination IP
        self.servertid = None  # destination port
        self.filename = None  # destination file
        self.last_sent = None  # in case of timeout during receive
        self.windowsize = 48
        self.hasher = hashlib.md5()
        self.sock.settimeout(timeout)

    def establish_connection(self):
        self.server = sys.argv[1]
        self.filename = sys.argv[2]
        self.servertid = default_port

        self.request = i2b(1) + self.filename.encode() + self.mode
        if self.windowsize > 1:
            self.request += b'windowsize\x00' + str(self.windowsize).encode() + b'\x00'

        # start connection
        self.sock.sendto(self.request, (self.server, self.servertid))
        self.last_sent = self.request

        # wait for answer
        while self.windowsize > 1:  # we do not want to receive data here
            package, sender = receive(self.sock, self.request, self.server, self.servertid)
            if package is None:
                print("connection lost")
                return
            self.server, self.servertid = sender[0], sender[1]
            if check_error(package): return  # error
            if package[:2] == i2b(3):  # no compromises
                print("not supported length of window")
                return
            if package[:2] == i2b(6):
                strings = package[2:].split(b'\x00')
                for opcode in range(len(strings)):
                    if strings[opcode] == b'windowsize':
                        self.windowsize = int(strings[opcode + 1].decode())
                        break
                break

        # RRQ
        if self.windowsize > 1:
            send_ack(self.sock, i2b(0), self.server, self.servertid)
            self.last_sent = i2b(4) + i2b(0)
        self.read_request()  # can start with receiving data
        print(self.hasher.hexdigest())

    def read_request(self):
        received = {}
        last_acked = 0
        full_block = True
        started = False
        while full_block:
            for i in range(self.windowsize):
                try:
                    data, sender = self.sock.recvfrom(4096)
                    if data == sender is None:
                        print("server not responding")
                        return

                    logging.debug("client receives package: {} from {}, {}".format(data, sender[0], sender[1]))

                    # validate speaker
                    if self.servertid == default_port and data[2:4] == i2b(1):
                        self.servertid = sender[1]  # remember for future validation
                        self.server = sender[0]
                    elif self.servertid != int(sender[1]) or self.server != sender[0]:
                        continue

                    # error
                    if check_error(data): return

                    # not data
                    if data[:2] != i2b(3): continue

                    received[b2i(data[2:4])] = data[4:]
                except socket.timeout:
                    break

            to_ack = last_acked
            while True:
                current = (to_ack + 1) % 2 ** 16
                if current in received.keys():
                    if len(received[current]) < 512: full_block = False
                    self.hasher.update(received[current])
                    # here you can see what has just come:
                    # print(received[current])
                    del received[current]
                    to_ack = current
                else:
                    break
            last_acked = to_ack
            if last_acked > 0: started = True
            if not started and self.windowsize == 1 and last_acked == 0:
                self.sock.sendto(self.request, (self.server, self.servertid))
            else:
                send_ack(self.sock, i2b(to_ack), self.server, self.servertid)


#logging.basicConfig(level='DEBUG')
client = clientTFTP()
client.establish_connection()
