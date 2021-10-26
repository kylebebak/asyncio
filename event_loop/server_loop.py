"""
https://docs.python.org/3/howto/sockets.html

Combine server with loop so we write server that creates a single server socket,
accepts connections (gets client sockets that represent connections), then can
read input from client over these "client" sockets and write responses to them.

When accepting connection, set socket to non-blocking mode and register client
socket with selector. In loop, call select and wait for server socket that's
ready to accept new connection, or client socket that's ready for writing or
reading.

Ready for writing means that outbound network buffer, write buffer, has space
available, because it was empty to begin with, or it was previously full, but
client has read data from it and now we can write more data to it. If it's full
and we try to write to it, a socket.error would be raised, but we don't need to
worry about this, because again, select ensures there's space in the outbound
write buffer. Maybe it's even totally empty.

Ready for reading means that inbound network buffer, read buffer, is NOT EMPTY,
i.e. there's at least something in it you can read that was written to the
buffer by the other end of the connection. Default buffer size for network
socket buffer is 8kb, which is not so big that you waste memory, and not so
small that you're calling send and recv too frequently.

When we get a connection, call an async function that yields immediately. Resume
it once there is data ready to read in recv buffer, and pass in the data. This
function should call an async handler that returns a response string or bytes,
then we yield again. Once there is empty space in send buffer, proceed to write
all of response string to write buffer.

Do this with several functions at once, and make sure async handler can do
things like sleep, etc. Now I'm getting closer to an async web server that can
serve a bunch of connections on a single thread.
"""

import asyncio
import selectors
import socket
import sys
import types
import threading
from typing import cast

sel = selectors.DefaultSelector()

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
port = int(sys.argv[1])  # Port to listen on (non-privileged ports are > 1023)

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((HOST, port))

# The argument to listen tells the socket library that we want it to
# queue up as many as 5 connect requests (the normal max) before refusing
# outside connections. If the rest of the code is written properly, that should
# be plenty.
lsock.listen(5)
print("listening on", (HOST, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)


def accept_connection(sock: socket.socket):
    """
    Accept connection on "server" socket
    """

    # This call blocks, but "server" socket is ready for reading
    conn, addr = sock.accept()
    # We call accept on "server" socket, We get a "client" socket `conn` that we
    # can write to and read from to communicate with client, it represents
    # connection between client and server

    print("accepted connection from", addr)  # This is address of the client
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
        # Socket is ready for reading
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
            # Socket is ready for writing; should always be the case with a healthy socket
            sent = sock.send(data.outb)
            # Remove number of bytes sent from send buffer
            data.outb = data.outb[sent:]


async def async_handle(sent: bytes):
    await asyncio.sleep(5)
    return sent + b" echoed"


async def io_handle():
    sent: bytes = yield
    response = await async_handle(sent)
    yield response


def io_thread_fn():
    # Event loop
    while True:
        # This call blocks until there's a socket ready for I/O
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                # Event is from listening "server" socket; accept connection and create client socket
                accept_connection(cast(socket.socket, key.fileobj))
            else:
                # Event is from client socket that's already been accepted
                service_connection(key, mask)


io_thread = threading.Thread(target=io_thread_fn)
io_thread.start()
