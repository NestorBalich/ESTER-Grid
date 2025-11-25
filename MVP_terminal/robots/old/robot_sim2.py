# ===============================================
# ESTER-Grid Robot Sim (EGUP v3) + AutoSquareWalk
# Python - UDP Robot Simulation
# Mantiene posición real, soporta comandos extensibles
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
res = requests.post(f"{SERVER}/register", json={"robotName": ROBOT_ID})
info = res.json()

# Usar puerto fijo del robot
UDP_PORT = info["port_robot_sim"]
DISPATCHER_ADDR = ("127.0.0.1", 9999)

print(f"[{ROBOT_ID}] UDP assigned:", UDP_PORT)

# UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

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

last_gps_sent = [state["pos"][0], state["pos"][1]]
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
            send_info = True

        # Enviar colisión solo si cambia
        if state["collision"] != last_collision_sent and state["collision"]:
            last_collision_sent = state["collision"]
            send_info = True

        if send_info:
            sock.sendto(json.dumps(packet).encode(), DISPATCHER_ADDR)

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

        if packet.get("type") == "cmd":
            cmd = packet["cmd"]
            val = packet.get("data", {}).get("value")
            steps = packet.get("data", {}).get("steps", 1)

            if cmd == "move":
                angle_rad = math.radians(state["rot"])
                state["pos"][0] += steps * math.cos(angle_rad)
                state["pos"][1] += steps * math.sin(angle_rad)

            elif cmd == "rotate":
                if val == "left":
                    state["rot"] = (state["rot"] - steps) % 360
                elif val == "right":
                    state["rot"] = (state["rot"] + steps) % 360

            elif cmd == "teleport":
                x = packet["data"].get("x")
                y = packet["data"].get("y")
                if x is not None: state["pos"][0] = x
                if y is not None: state["pos"][1] = y

            elif cmd == "set_collision":
                state["collision"] = bool(packet["data"].get("collision", False))

        elif packet.get("type") == "state_info":
            data = packet.get("data", {})
            gps = data.get("gps")
            collision = data.get("collision")

            if gps and len(gps) >= 2:
                state["pos"][0] = gps[0]
                state["pos"][1] = gps[1]

            if collision is not None:
                state["collision"] = collision

# ------------------------------------------
# AUTO MOVEMENT: RANDOM START + SQUARE WALK
def auto_square():
    global auto_started, step_counter, turning, turn_target
    time.sleep(0.5)
    state["pos"][0] = random.randint(50, 450)
    state["pos"][1] = random.randint(50, 450)
    state["rot"] = random.choice([0, 90, 180, 270])
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

        time.sleep(0.02)

# ------------------------------------------
# START THREADS
threading.Thread(target=send_state, daemon=True).start()
threading.Thread(target=receiver, daemon=True).start()
threading.Thread(target=auto_square, daemon=True).start()

print(f"[{ROBOT_ID}] Simulation running with color: {robot_color}")

while True:
    time.sleep(1)
