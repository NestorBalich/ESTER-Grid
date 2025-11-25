# ===============================================
# Robot UDP Teleport / Move / Sensors / Collisions
# Python - Socket.IO + UDP
# ===============================================

import socket
import json
import time
import random
import threading
import socketio
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True)
parser.add_argument("--dispatcher_host", default="127.0.0.1")
parser.add_argument("--dispatcher_port", type=int, default=6029)
args = parser.parse_args()

ROBOT_ID = args.name
DISPATCHER_HOST = args.dispatcher_host
DISPATCHER_PORT = args.dispatcher_port

# Estado interno
robot_state = {"pos": [450, 180], "rot": 0, "color": (255, 100, 50)}

# UDP sockets
UDP_SEND_PORT = None   # puerto del dispatcher al que el robot enviará
UDP_RECV_PORT = None   # puerto propio donde robot hace bind para recibir
sock_send = None
sock_recv = None

# Funciones
def teletransportar_random():
    x = random.randint(50, 850)
    y = random.randint(50, 350)
    rot = random.randint(0, 359)
    robot_state["pos"] = [x, y]
    robot_state["rot"] = rot
    return x, y, rot

def send_packet(cmd=None, cmd_data=None):
    if not sock_send:
        return
    packet = {"src": ROBOT_ID, "dst": "sim_server", "type": "state", "data": robot_state, "ts": int(time.time()*1000)}
    if cmd:
        packet["cmd"] = cmd
        packet["cmdData"] = cmd_data
    sock_send.sendto(json.dumps(packet).encode(), ("127.0.0.1", UDP_SEND_PORT))
    print(f"[{ROBOT_ID}] Enviado UDP {UDP_SEND_PORT}: {packet}")

def receive_loop():
    while True:
        try:
            msg, addr = sock_recv.recvfrom(4096)
            packet = json.loads(msg.decode())
            print(f"[{ROBOT_ID}] Recibido UDP {UDP_RECV_PORT}: {packet}")
        except Exception:
            pass

# Socket.IO
sio = socketio.Client()

@sio.event
def connect():
    print(f"[{ROBOT_ID}] Conectado al dispatcher")

@sio.on("udp_ports")
def on_udp_ports(data):
    global UDP_SEND_PORT, UDP_RECV_PORT, sock_send, sock_recv
    UDP_SEND_PORT = data["send"]   # donde robot envía al dispatcher
    UDP_RECV_PORT = data["recv"]   # puerto propio donde robot hace bind

    print(f"[{ROBOT_ID}] Puertos asignados: send={UDP_SEND_PORT}, recv={UDP_RECV_PORT}")

    sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock_recv.bind(("", UDP_RECV_PORT))
    except Exception as e:
        print(f"[{ROBOT_ID}] ERROR al bindear UDP {UDP_RECV_PORT}: {e}")

    threading.Thread(target=receive_loop, daemon=True).start()

sio.connect(f"http://{DISPATCHER_HOST}:{DISPATCHER_PORT}")

# Loop principal
while True:
    x, y, rot = teletransportar_random()
    send_packet("teleport", {"pos": [x, y], "rot": rot})
    time.sleep(5)
