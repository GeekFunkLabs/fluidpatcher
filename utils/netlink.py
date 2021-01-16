"""
Copyright (c) 2020 Bill Peterson

Description: tools for controlling patcher over a network
"""
import socket, select
from time import time_ns

DEFAULT_PORT = 8675
DEFAULT_PASSKEY = 'a9b8d3'
BUFSIZE = 1024

# request types
SEND_VERSION = 11
RECV_BANK = 12
LIST_BANKS = 13
LOAD_BANK = 14
SAVE_BANK = 15
SELECT_PATCH = 16
LIST_SOUNDFONTS = 17
LOAD_SOUNDFONT = 18
SELECT_SFPRESET = 19
LIST_PLUGINS = 20
LIST_PORTS = 21
READ_CFG = 22
SAVE_CFG = 23
# to be implemented(?):
# SOFTWARE_UPDATE

# reply types
MSG_INVALID = -1
NO_COMM = 0
REQ_OK = 1
REQ_ERROR = 2

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


class Server:

    def __init__(self, port=DEFAULT_PORT, passkey=DEFAULT_PASSKEY):
        self.passkey = passkey
        self.port = port

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFSIZE)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(0)

        self.inputs = []
        self.requests = []

    def __del__(self):
        self.socket.close()

    def pending(self):
        if self.socket not in self.inputs:
            netaddr = get_ip()
            if netaddr in ['127.0.0.1', 'localhost', 'raspberrypi']:
                return []
            try:
                self.socket.bind((netaddr, self.port))
            except:
                pass # just keep trying if the socket is in use
            else:
                self.socket.listen(5)
                self.inputs = [self.socket]
            
        while True:
            readable, writable, errored = select.select(self.inputs, [], [], 0)
            if not readable: break
            for sock in readable:
                if sock == self.socket:
                    conn, address = self.socket.accept()
                    self.inputs.append(conn)
                    continue
                req = Message(sock)
                if req.type == NO_COMM or req.passkey != self.passkey:
                    sock.close()
                    self.inputs.remove(sock)
                    continue
                if req.type == MSG_INVALID:
                    continue
                self.requests.append(req)
        return self.requests

    def reply(self, req, response='', type=REQ_OK):
        msg = Message(type=type, passkey=self.passkey, body=str(response), id=req.id)
        try:
            req.origin.sendall(msg.content)
        except:
            pass

class Client:

    def __init__(self, server='', port=DEFAULT_PORT, passkey=DEFAULT_PASSKEY, timeout=20):
        self.passkey = passkey
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFSIZE)
        self.pending = []

        if server:
            self.socket.connect((server, port))
        else:
            self.socket.connect((socket.gethostname(), port))

    def request(self, type, body='', blocking=1):
        req = Message(type=type, passkey=self.passkey, body=str(body))
        self.socket.sendall(req.content)
        if blocking:
            reply = Message(self.socket)
            return reply
        self.pending.append(req)

    def check(self):
    # only need this if non-blocking
        if self.pending == []:
            return None
        readable, writable, errored = select.select([self.socket], [], [], 0)
        if self.socket in readable:
            reply = Message(self.socket)
            for req in self.pending:
                if req.id == reply.id:
                    self.pending.remove(req)
                    return reply
                    break
        return None

    def close(self):
        self.socket.close()

class Message:

    def __init__(self, origin=None, type=None, passkey='', body='', id=0):
        self.origin = origin

        if origin:
            try:
                hdr = origin.recv(40)
            except:
                self.type = NO_COMM
                return
            if len(hdr) == 0:
                self.type = NO_COMM
                return
            if len(hdr) < 40:
                self.type = MSG_INVALID
                return
            try:
                self.type, self.passkey, msglen, self.id = int(hdr[0:2]), hdr[3:9].decode(), int(hdr[9:19]), int(hdr[19:40])
            except ValueError:
                self.type = MSG_INVALID
                return
            msg = b''
            while len(msg) < msglen:
                b = origin.recv(min(BUFSIZE, msglen - len(msg)))
                if len(b) == 0:
                    self.type = NO_COMM
                    return
                msg += b
            self.body = msg.decode()
            self.content = hdr + msg
        else:
            self.type = type
            self.passkey = passkey
            self.body = body
            if id > 0:
                self.id = id
            else:
                self.id = time_ns()
            hdr = '%2s%7s%10s%21s' % (type, passkey, len(body), self.id)
            self.content = hdr.encode() + body.encode()

