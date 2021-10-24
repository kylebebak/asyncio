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
