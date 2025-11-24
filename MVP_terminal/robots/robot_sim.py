# ===============================================
# ESTER-Grid Robot Sim (EGUP v2) + AutoSquareWalk
# Python - UDP Robot Simulation
# Muestra mensajes enviados (GPS / Colisión), color aleatorio y estado del mapa
# ===============================================

import socket
import json
import time
import threading
import requests
import argparse
import random
import math

parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True, help="Robot ID")
parser.add_argument("--server", default="http://localhost:4000")
args = parser.parse_args()

ROBOT_ID = args.name
SERVER = args.server

# ------------------------------------------
# 1. Register at dispatcher
# ------------------------------------------
res = requests.post(f"{SERVER}/register", json={"robot": ROBOT_ID})
info = res.json()
UDP_PORT = info["udp_port"]

print(f"[{ROBOT_ID}] UDP assigned:", UDP_PORT)

# UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

DISPATCHER_ADDR = ("127.0.0.1", 9999)

# Robot movement parameters
SPEED = 1
TURN_SPEED = 5
SQUARE_SIDE = 100

# ------------------------------------------
# Robot state
robot_color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
state = {
    "pos": [0, 0, 0],  # x, y, forward
    "rot": 0,
    "collision": False,
    "color": robot_color
}

last_gps_sent = [state["pos"][0], state["pos"][1]]  # para comparar cambios
last_collision_sent = None

# ------------------------------------------
# Automatic movement variables
auto_started = False
step_counter = 0
turning = False
turn_target = 0

# ------------------------------------------
# SEND STATE LOOP
def send_state():
    global last_gps_sent, last_collision_sent
    while True:
        state["color"] = robot_color
        packet = {
            "src": ROBOT_ID,
            "dst": "dispatcher",
            "type": "state",
            "data": state,
            "ts": int(time.time() * 1000)
        }

        send_info = False
        info_text = ""

        # Enviar GPS solo si cambia
        if state["pos"][0] != last_gps_sent[0] or state["pos"][1] != last_gps_sent[1]:
            last_gps_sent = [state["pos"][0], state["pos"][1]]
            info_text += f"GPS sent -> pos: {state['pos']} "
            send_info = True

        # Enviar colisión solo si cambia
        if state["collision"] != last_collision_sent and state["collision"]:
            last_collision_sent = state["collision"]
            info_text += f"Collision sent -> {state['collision']} "
            send_info = True

        if send_info:
            sock.sendto(json.dumps(packet).encode(), DISPATCHER_ADDR)
            #print(f"[{ROBOT_ID}] Sent packet: {info_text.strip()} Color: {robot_color}")

        time.sleep(0.05)

# ------------------------------------------
# RECEIVER (manual dispatcher commands + map updates)
def receiver():
    while True:
        msg, addr = sock.recvfrom(4096)
        try:
            packet = json.loads(msg.decode())
        except Exception:
            print(f"[{ROBOT_ID}] Received non-JSON packet: {msg}")
            continue

        print(f"[{ROBOT_ID}] Received packet: {packet}")

        if packet.get("type") == "cmd":
            cmd = packet["cmd"]
            val = packet.get("data", {}).get("value")
            steps = packet.get("data", {}).get("steps", 1)

            if cmd == "move":
                dx = steps * math.cos(math.radians(state["rot"]))
                dy = steps * math.sin(math.radians(state["rot"]))
                state["pos"][0] += dx
                state["pos"][1] += dy

            elif cmd == "rotate":
                if val == "left":
                    state["rot"] -= 10
                elif val == "right":
                    state["rot"] += 10

        elif packet.get("type") == "state_info":
            data = packet.get("data", {})
            gps = data.get("gps")
            collision = data.get("collision")

            if gps and len(gps) >= 2:
                state["pos"][0] = gps[0]
                state["pos"][1] = gps[1]

            if collision is not None:
                state["collision"] = collision

            print(f"[{ROBOT_ID}] Updated state from map -> pos: {state['pos']} collision: {state['collision']}")

# ------------------------------------------
# AUTO MOVEMENT: RANDOM START + SQUARE WALK
def auto_square():
    global auto_started, step_counter, turning, turn_target
    time.sleep(0.5)
    state["pos"][0] = random.randint(50, 450)
    state["pos"][1] = random.randint(50, 450)
    state["rot"] = random.choice([0, 90, 180, 270])
    print(f"[{ROBOT_ID}] Random start -> X={state['pos'][0]} Y={state['pos'][1]} Rot={state['rot']} Color={robot_color}")
    auto_started = True
    step_counter = 0
    turning = False
    turn_target = 0

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
                #print(f"[{ROBOT_ID}] Turn completed -> new rot: {state['rot']}")

        time.sleep(0.02)

# ------------------------------------------
# START THREADS
threading.Thread(target=send_state, daemon=True).start()
threading.Thread(target=receiver, daemon=True).start()
threading.Thread(target=auto_square, daemon=True).start()

print(f"[{ROBOT_ID}] Simulation running with color: {robot_color}")

while True:
    time.sleep(1)
