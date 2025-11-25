# ===============================================
# ESTER-Grid Robot Mesh Messaging
# Send direct robot-to-robot messages via dispatcher
# ===============================================
import socket
import json
import time
import argparse

DISPATCHER = ("127.0.0.1", 9999)


def send_mesh(src_robot, dst_robot, cmd, value=None, dispatcher=DISPATCHER):
    packet = {
        "src": src_robot,
        "dst": dst_robot,
        "type": "cmd",
        "cmd": cmd,
        "data": {"value": value} if value is not None else {},
        "ts": int(time.time() * 1000)
    }

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(packet).encode(), dispatcher)
    print(f"[Mesh] {src_robot} → {dst_robot}: {cmd} {value if value else ''}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a mesh command via dispatcher")
    parser.add_argument('--from', dest='src', required=True, help='Source robot id')
    parser.add_argument('--to', dest='dst', required=True, help='Destination robot id')
    parser.add_argument('--cmd', required=True, help='Command name')
    parser.add_argument('--value', help='Command value (optional)')
    parser.add_argument('--dispatcher', default='127.0.0.1:9999', help='Dispatcher address host:port')

    args = parser.parse_args()

    host, port = args.dispatcher.split(':')
    dispatcher_addr = (host, int(port))

    send_mesh(args.src, args.dst, args.cmd, args.value, dispatcher=dispatcher_addr)
