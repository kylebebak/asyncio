import selectors
import socket
import sys
import types
from typing import cast

sel = selectors.DefaultSelector()

HOST = "127.0.0.1"
messages = [b"Message 1 from client.", b"Message 2 from client."]


def start_connections(host: str, port: int, num_conns: int):
    server_addr = (host, port)
    for i in range(0, num_conns):
        connid = i + 1
        print("starting connection", connid, "to", server_addr)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(
            connid=connid,
            msg_total=sum(len(m) for m in messages),
            recv_total=0,
            messages=list(messages),
            outb=b"",
        )
        sel.register(sock, events, data=data)


def service_connection(key: selectors.SelectorKey, mask: int):
    sock = cast(socket.socket, key.fileobj)
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            print("received", repr(recv_data), "from connection", data.connid)
            data.recv_total += len(recv_data)
        if not recv_data or data.recv_total == data.msg_total:
            print("closing connection", data.connid)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        if data.outb:
            print("sending", repr(data.outb), "to connection", data.connid)
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


start_connections(host=HOST, port=int(sys.argv[1]), num_conns=int(sys.argv[2]))


while True:
    events = sel.select(timeout=None)
    for key, mask in events:
        # Event is from client socket that's already been accepted
        service_connection(key, mask)
