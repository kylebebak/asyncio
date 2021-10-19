# https://realpython.com/python-sockets/
# https://docs.python.org/3/library/socket.html#socket.socket.recv
# https://docs.python.org/3/library/select.html#select.select
# https://stackoverflow.com/questions/49005651/how-does-asyncio-actually-work

import socket

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    while True:
        conn, addr = s.accept()
        print("socket", s.fileno(), s)
        print("connected by", addr)
        with conn:
            while True:
                data = conn.recv(1024)
                print(f"server receieved and sent {data}")
                if not data:
                    break
                conn.sendall(data)
