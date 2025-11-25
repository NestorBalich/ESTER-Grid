# ===============================================
# ESTER-Grid Robot Sim (EGUP v3) + AutoSquareWalk Centered
# Python - UDP Robot Simulation con Dispatcher dinámico
# ===============================================

import socket
import json
import time
import threading
import math
import random
import socketio

# ------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------
ROBOT_ID = "ROB1"  # Cambiar si hay más robots
DISPATCHER_SERVER = "http://127.0.0.1:6029"  # Dispatcher Socket.IO
SPEED = 1           # px por tick
TURN_SPEED = 5      # grados por tick
SQUARE_SIDE = 100   # tamaño del cuadrado en px
CENTER_POS = [400, 400]  # centro del cuadrado

# ------------------------------------------
# ESTADO DEL ROBOT
# ------------------------------------------
robot_color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
state = {
    "pos": [0, 0],
    "rot": 0,
    "collision": False,
    "color": robot_color
}

last_gps_sent = [state["pos"][0], state["pos"][1]]
last_collision_sent = None

# ------------------------------------------
# SOCKET.IO CLIENTE PARA PUERTOS DINÁMICOS
# ------------------------------------------
sio = socketio.Client()
udp_send_port = None
udp_recv_port = None
sock_send = None
sock_recv = None

@sio.event
def connect():
    print(f"[{ROBOT_ID}] Conectado al dispatcher")

@sio.on("udp_ports")
def on_udp_ports(data):
    global udp_send_port, udp_recv_port, sock_send, sock_recv
    udp_send_port = data["send"]
    udp_recv_port = data["recv"]
    print(f"[{ROBOT_ID}] Puertos asignados: send={udp_send_port}, recv={udp_recv_port}")

    # Crear sockets UDP
    sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock_recv.bind(("0.0.0.0", udp_recv_port))
    except Exception as e:
        print(f"[{ROBOT_ID}] ERROR al bindear UDP {udp_recv_port}: {e}")

    # Hilo receptor
    threading.Thread(target=receiver, daemon=True).start()

sio.connect(DISPATCHER_SERVER)

# ------------------------------------------
# FUNCIONES
# ------------------------------------------

def send_state():
    global last_gps_sent, last_collision_sent
    while True:
        if not sock_send or not udp_send_port:
            time.sleep(0.1)
            continue

        packet = {
            "src": ROBOT_ID,
            "type": "state",
            "data": state,
            "ts": int(time.time() * 1000)
        }

        send_info = False
        if state["pos"][0] != last_gps_sent[0] or state["pos"][1] != last_gps_sent[1]:
            last_gps_sent = [state["pos"][0], state["pos"][1]]
            send_info = True

        if state["collision"] != last_collision_sent and state["collision"]:
            last_collision_sent = state["collision"]
            send_info = True

        if send_info:
            try:
                sock_send.sendto(json.dumps(packet).encode(), ("127.0.0.1", udp_send_port))
            except Exception as e:
                print(f"[{ROBOT_ID}] ERROR al enviar UDP: {e}")

        time.sleep(0.05)

def receiver():
    while True:
        try:
            msg, addr = sock_recv.recvfrom(4096)
            packet = json.loads(msg.decode())
        except Exception:
            continue

        if packet.get("type") == "cmd":
            cmd = packet["cmd"]
            val = packet.get("data", {}).get("value")
            steps = packet.get("data", {}).get("steps", 1)

            if cmd == "move":
                angle_rad = math.radians(state["rot"])
                state["pos"][0] += steps * math.cos(angle_rad)
                state["pos"][1] += steps * math.sin(angle_rad)
            elif cmd == "rotate":
                if val == "left": state["rot"] = (state["rot"] - steps) % 360
                elif val == "right": state["rot"] = (state["rot"] + steps) % 360
            elif cmd == "teleport":
                x = packet["data"].get("x")
                y = packet["data"].get("y")
                rot = packet["data"].get("rot")
                if x is not None: state["pos"][0] = x
                if y is not None: state["pos"][1] = y
                if rot is not None: state["rot"] = rot
                print(f"[{ROBOT_ID}] Teletransportado a x={state['pos'][0]}, y={state['pos'][1]}, rot={state['rot']}°")

def send_packet(cmd=None, cmd_data=None):
    if not sock_send:
        return
    packet = {"src": ROBOT_ID, "dst": "sim_server", "type": "state", "data": state, "ts": int(time.time()*1000)}
    if cmd:
        packet["cmd"] = cmd
        packet["cmdData"] = cmd_data
    sock_send.sendto(json.dumps(packet).encode(), ("127.0.0.1", udp_send_port))
    print(f"[{ROBOT_ID}] Enviado UDP {udp_send_port}: {packet}")


def auto_square_centered():
    start_x = 400
    start_y = 180
    state["pos"][0] = start_x
    state["pos"][1] = start_y
    state["rot"] = 0
    send_packet("teleport", {"pos": [state["pos"][0], state["pos"][1]], "rot":  state["rot"]})
    
    print(f"[{ROBOT_ID}] Comenzando cuadrado centrado en x={start_x}, y={start_y}")

    step_counter = 0
    turning = False
    turn_target = 0

   
    time.sleep(1)

    while True:
        if not turning:
            angle_rad = math.radians(state["rot"])
            state["pos"][0] += SPEED * math.cos(angle_rad)
            state["pos"][1] += SPEED * math.sin(angle_rad)
            step_counter += SPEED

            if step_counter >= SQUARE_SIDE:
                turning = True
                turn_target = (state["rot"] + 90) % 360
        else:
            state["rot"] = (state["rot"] + TURN_SPEED) % 360
            if abs(state["rot"] - turn_target) < TURN_SPEED:
                state["rot"] = turn_target
                turning = False
                step_counter = 0

        time.sleep(0.02)

# ------------------------------------------
# INICIAR HILOS
# ------------------------------------------
threading.Thread(target=send_state, daemon=True).start()
threading.Thread(target=auto_square_centered, daemon=True).start()

print(f"[{ROBOT_ID}] Simulation running with color: {robot_color}")

while True:
    time.sleep(1)
