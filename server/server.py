"""
https://realpython.com/python-sockets/#handling-multiple-connections

https://docs.python.org/3/howto/sockets.html

Now we come to the major stumbling block of sockets - send and recv operate on
the network buffers. They do not necessarily handle all the bytes you hand them
(or expect from them), because their major focus is handling the network
buffers. In general, they return when the associated network buffers have been
filled (send) or emptied (recv). They then tell you how many bytes they handled.
It is your responsibility to call them again until your message has been
completely dealt with.

In Python, you use socket.setblocking(False) to make it non-blocking. In C, it’s
more complex, (for one thing, you’ll need to choose between the BSD flavor
O_NONBLOCK and the almost indistinguishable POSIX flavor O_NDELAY, which is
completely different from TCP_NODELAY), but it’s the exact same idea. You do
this after creating the socket, but before using it. (Actually, if you’re nuts,
you can switch back and forth.)

The major mechanical difference is that send, recv, connect and accept can
return without having done anything. You have (of course) a number of choices.
You can check return code and error codes and generally drive yourself crazy. If
you don’t believe me, try it sometime. Your app will grow large, buggy and suck
CPU. So let’s skip the brain-dead solutions and do it right.

Use select.

If a socket is in the output readable list, you can be
as-close-to-certain-as-we-ever-get-in-this-business that a recv on that socket
will return something. Same idea for the writable list. You’ll be able to send
something. Maybe not all you want to, but something is better than nothing.
(Actually, any reasonably healthy socket will return as writable - it just means
outbound network buffer space is available.)

But if you plan to reuse your socket for further transfers, you need to realize
that there is no EOT on a socket. I repeat: if a socket send or recv returns
after handling 0 bytes, the connection has been broken. If the connection has
not been broken, you may wait on a recv forever, because the socket will not
tell you that there’s nothing more to read (for now). Now if you think about
that a bit, you’ll come to realize a fundamental truth of sockets: messages must
either be fixed length (yuck), or be delimited (shrug), or indicate how long
they are (much better), or end by shutting down the connection. The choice is
entirely yours, (but some ways are righter than others).

-----

https://medium.com/vaidikkapoor/understanding-non-blocking-i-o-with-python-part-1-ec31a2e2db9b

import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 1234))
sock.setblocking(0)

data = 'foobar\n' * 10 * 1024 * 1024  # 70 MB of data
assert sock.send(data) == len(data)  # AssertionError

When you run the above client, you will notice that it did not block at all. But
there is a problem with the client — it did not send all the data. socket.send
method returns the number of bytes sent. When you make a socket non-blocking by
calling setblocking(0), it will never wait for the operation to complete. So
when you call the send() method, it will put as much data in the buffer as
possible and return. As this is read by the remote connection, the data is
removed from the buffer. If the buffer gets full and we continue to send data,
socket.error will be raised. When you try to send data more than the buffer can
accommodate, only the amount of data that can be accommodated is actually sent
and send() returns the number of bytes sent. This is useful so that we can try
to send the remaining data when the buffer becomes empty. Let’s try to achieve
that:
"""

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


# Event loop
while True:
    events = sel.select(timeout=None)
    for key, mask in events:
        if key.data is None:
            # Event is from listening "server" socket; accept connection and create client socket
            accept_connection(cast(socket.socket, key.fileobj))
        else:
            # Event is from client socket that's already been accepted
            service_connection(key, mask)
