import selectors
import socket
import sys
import types
from typing import cast

sel = selectors.DefaultSelector()

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
port = int(sys.argv[1])  # Port to listen on (non-privileged ports are > 1023)

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((HOST, port))
lsock.listen()
print("listening on", (HOST, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)


def accept_connection(sock: socket.socket):
    """
    Accept connection on socket
    """

    # This call blocks, but socket is ready for reading
    conn, addr = sock.accept()
    print("accepted connection from", addr)
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    sel.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data=data)


def service_connection(key: selectors.SelectorKey, mask: int):
    """
    Read data from client socket
    """

    sock = cast(socket.socket, key.fileobj)
    data = key.data
    if mask & selectors.EVENT_READ:
        # Call blocks, but socket is ready for reading
        recv_data = sock.recv(1024)
        if recv_data:
            data.outb += recv_data
        else:
            print("closing connection to", data.addr)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(f"echoing {data.outb} to {data.addr}")
            # Call blocks, but socket is ready for writing
            sent = sock.send(data.outb)
            # Remove number of bytes sent from send buffer
            data.outb = data.outb[sent:]


# Event loop
while True:
    events = sel.select(timeout=None)
    for key, mask in events:
        if key.data is None:
            # Event is from listening socket; accept connection
            accept_connection(cast(socket.socket, key.fileobj))
        else:
            # Event is from client socket that's already been accepted
            service_connection(key, mask)
