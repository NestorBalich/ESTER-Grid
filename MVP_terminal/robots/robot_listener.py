import socket

PORT = int(input("Listen UDP port: "))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))

print("Listening on", PORT)

while True:
    msg, addr = sock.recvfrom(4096)
    print(f"{addr} →", msg.decode())
