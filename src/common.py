#!/usr/bin/env python3

import logging
import socket

attempts = 10000
timeout = 0.1
default_port = 6969


###
#
# common methods
#
###

def i2b(integer):
    return int(integer).to_bytes(2, 'big')


def b2i(byte):
    return int.from_bytes(byte, 'big')


def check_error(data):
    if data[:2] == i2b(5):
        print("Error occurred:\ncode: {}\nmessage: {}".format(b2i(data[2:4]), data[4:-1].decode()))
        return True
    return False


def send_ack(sock, block, dst, dst_port):
    logging.debug("sending ACK of block {}".format(b2i(block)))
    sock.sendto(i2b(4) + block, (dst, dst_port))


def send_data(sock, block, data, dst, dst_port):
    logging.debug("sending data {} of length {}".format(data, len(data)))
    sock.sendto(i2b(3) + block + data, (dst, dst_port))


def send_oack(sock, windowsize, dst, dst_port):
    logging.debug("sending OACK(windowsize {})".format(windowsize))
    msg = i2b(6) + b'windowsize\x00' + str(windowsize).encode() + b'\x00'
    sock.sendto(msg, (dst, dst_port))
    return msg


def receive(sock, last_sent, dst, dst_port):
    for i in range(attempts):
        try:
            return sock.recvfrom(4096)
        except socket.timeout:
            if last_sent is None:
                continue
            elif not isinstance(last_sent, list):
                sock.sendto(last_sent, (dst, dst_port))
            else:
                for msg in last_sent:
                    sock.sendto(msg, (dst, dst_port))
    return None, None
