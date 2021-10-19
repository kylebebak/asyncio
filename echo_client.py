import socket
import time

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server

count = 0

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    while True:
        s.sendall(f"Hello {count}".encode())
        data = s.recv(1024)
        print(f"client sent and received {data}")

        count += 1
        time.sleep(3)
