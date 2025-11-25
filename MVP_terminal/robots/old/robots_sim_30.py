# =====================================================
# EGUP v3 - Multi-Robot Simulation (30 Robots)
# Cada robot se registra en dispatcher y usa UDP fijo
# Robots: ROB1 - ROB30
# =====================================================

import socket
import json
import time
import threading
import requests
import random
import math

SERVER = "http://localhost:4000"
DISPATCHER_ADDR = ("127.0.0.1", 9999)

NUM_ROBOTS = 30
SPEED = 1
TURN_SPEED = 5
SQUARE_SIDE = 100

class Robot:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.color = (random.randint(50,255), random.randint(50,255), random.randint(50,255))
        self.state = {
            "pos": [0,0,0],
            "rot": 0,
            "collision": False,
            "color": self.color
        }
        self.last_gps_sent = [0,0]
        self.last_collision_sent = None
        self.step_counter = 0
        self.turning = False
        self.turn_target = 0
        self.auto_started = False

        # Registrar robot y obtener UDP port
        res = requests.post(f"{SERVER}/register", json={"robotName": self.robot_id})
        info = res.json()
        self.udp_port = info["port_robot_sim"]
        print(f"[{self.robot_id}] UDP assigned:", self.udp_port)

        # Crear socket UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.udp_port))

    # Enviar estado al dispatcher
    def send_state(self):
        while True:
            self.state["color"] = self.color
            packet = {
                "src": self.robot_id,
                "dst": "dispatcher",
                "type": "state",
                "data": self.state,
                "ts": int(time.time()*1000)
            }

            send_info = False
            if self.state["pos"][0] != self.last_gps_sent[0] or self.state["pos"][1] != self.last_gps_sent[1]:
                self.last_gps_sent = self.state["pos"][:2]
                send_info = True
            if self.state["collision"] != self.last_collision_sent and self.state["collision"]:
                self.last_collision_sent = self.state["collision"]
                send_info = True

            if send_info:
                self.sock.sendto(json.dumps(packet).encode(), DISPATCHER_ADDR)

            time.sleep(0.05)

    # Recibir comandos desde dispatcher
    def receiver(self):
        while True:
            msg, addr = self.sock.recvfrom(4096)
            try:
                packet = json.loads(msg.decode())
            except Exception:
                print(f"[{self.robot_id}] Received non-JSON packet:", msg)
                continue

            if packet.get("type") == "cmd":
                cmd = packet["cmd"]
                val = packet.get("data", {}).get("value")
                steps = packet.get("data", {}).get("steps", 1)

                if cmd == "move":
                    angle_rad = math.radians(self.state["rot"])
                    self.state["pos"][0] += steps * math.cos(angle_rad)
                    self.state["pos"][1] += steps * math.sin(angle_rad)
                elif cmd == "rotate":
                    if val == "left":
                        self.state["rot"] = (self.state["rot"] - steps) % 360
                    elif val == "right":
                        self.state["rot"] = (self.state["rot"] + steps) % 360
                elif cmd == "teleport":
                    x = packet["data"].get("x")
                    y = packet["data"].get("y")
                    if x is not None: self.state["pos"][0] = x
                    if y is not None: self.state["pos"][1] = y
                elif cmd == "set_collision":
                    self.state["collision"] = bool(packet["data"].get("collision", False))

            elif packet.get("type") == "state_info":
                data = packet.get("data", {})
                gps = data.get("gps")
                collision = data.get("collision")
                if gps and len(gps)>=2:
                    self.state["pos"][0] = gps[0]
                    self.state["pos"][1] = gps[1]
                if collision is not None:
                    self.state["collision"] = collision

    # Movimiento automático cuadrado
    def auto_square(self):
        time.sleep(0.5)
        self.state["pos"][0] = random.randint(50,450)
        self.state["pos"][1] = random.randint(50,450)
        self.state["rot"] = random.choice([0,90,180,270])
        self.auto_started = True
        self.step_counter = 0
        self.turning = False
        self.turn_target = 0

        while True:
            if not self.turning:
                angle_rad = math.radians(self.state["rot"])
                self.state["pos"][0] += SPEED * math.cos(angle_rad)
                self.state["pos"][1] += SPEED * math.sin(angle_rad)
                self.step_counter += SPEED
                if self.step_counter >= SQUARE_SIDE:
                    self.turning = True
                    self.turn_target = (self.state["rot"] + 90) % 360
            else:
                self.state["rot"] = (self.state["rot"] + TURN_SPEED) % 360
                if abs(self.state["rot"] - self.turn_target) < TURN_SPEED:
                    self.state["rot"] = self.turn_target
                    self.turning = False
                    self.step_counter = 0

            time.sleep(0.02)

    # Iniciar threads del robot
    def start(self):
        threading.Thread(target=self.send_state, daemon=True).start()
        threading.Thread(target=self.receiver, daemon=True).start()
        threading.Thread(target=self.auto_square, daemon=True).start()
        print(f"[{self.robot_id}] Simulation running with color: {self.color}")


# =====================================================
# Main: Crear y arrancar 30 robots
# =====================================================
robots = [Robot(f"ROB{i+1}") for i in range(NUM_ROBOTS)]

for r in robots:
    r.start()

# Mantener el programa vivo
while True:
    time.sleep(1)
