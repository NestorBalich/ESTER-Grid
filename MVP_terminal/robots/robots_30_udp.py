# =====================================================
# EGUP v3 - Multi-Robot Simulation con Dispatcher UDP dinámico
# =====================================================

import socket
import json
import time
import threading
import random
import math
import socketio

SERVER = "http://127.0.0.1:6029"  # Dispatcher Socket.IO
NUM_ROBOTS = 30
SPEED = 1
MIN_DIST = 30  # distancia mínima entre filas

# Estados
STATE_INICIAL = 0
STATE_GIRAR = 1
STATE_AVANZAR = 2
STATE_RETROCEDER = 3

# Formación
CENTER_X = 450
CENTER_Y_ARRIBA = 150
CENTER_Y_ABAJO = 250
HORIZONTAL_SPACING = 40  # separación entre robots

class Robot:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.color = (random.randint(50,255), random.randint(50,255), random.randint(50,255))
        self.state = {"pos":[0,0,0], "rot":0, "collision":False, "color":self.color}
        self.last_gps_sent = [0,0]
        self.last_collision_sent = None
        self.estado = STATE_INICIAL
        self.pos_inicial = [0,0]

        # Socket.IO cliente para recibir puertos UDP
        self.sio = socketio.Client()
        self.udp_send_port = None
        self.udp_recv_port = None
        self.sock_send = None
        self.sock_recv = None

        @self.sio.event
        def connect():
            print(f"[{self.robot_id}] Conectado al dispatcher")

        @self.sio.on("udp_ports")
        def on_udp_ports(data):
            self.udp_send_port = data["send"]
            self.udp_recv_port = data["recv"]
            print(f"[{self.robot_id}] Puertos asignados: send={self.udp_send_port}, recv={self.udp_recv_port}")

            # Crear sockets UDP
            self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                self.sock_recv.bind(("0.0.0.0", self.udp_recv_port))
            except Exception as e:
                print(f"[{self.robot_id}] ERROR al bindear UDP {self.udp_recv_port}: {e}")

            # Hilo receptor
            threading.Thread(target=self.receiver, daemon=True).start()

        self.sio.connect(SERVER)

    # Enviar estado al dispatcher
    def send_state(self):
        while True:
            if not self.sock_send or not self.udp_send_port:
                time.sleep(0.1)
                continue

            self.state["color"] = self.color
            # agregar robot_id dentro de data
            data_to_send = self.state.copy()
            data_to_send["name"] = self.robot_id

            packet = {
                "src": self.robot_id,
                "dst": "sim_server",
                "type": "state",
                "data": data_to_send,
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
                try:
                    self.sock_send.sendto(json.dumps(packet).encode(), ("127.0.0.1", self.udp_send_port))
                except Exception as e:
                    print(f"[{self.robot_id}] ERROR al enviar UDP: {e}")

            time.sleep(0.05)

    # Recibir comandos desde dispatcher
    def receiver(self):
        while True:
            try:
                msg, addr = self.sock_recv.recvfrom(4096)
                packet = json.loads(msg.decode())
            except Exception:
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
                    if val == "left": self.state["rot"] = (self.state["rot"] - steps) % 360
                    elif val == "right": self.state["rot"] = (self.state["rot"] + steps) % 360
                elif cmd == "teleport":
                    x = packet["data"].get("x")
                    y = packet["data"].get("y")
                    rot = packet["data"].get("rot")
                    if x is not None: self.state["pos"][0] = x
                    if y is not None: self.state["pos"][1] = y
                    if rot is not None: self.state["rot"] = rot
                    print(f"[{self.robot_id}] Teletransportado a x={self.state['pos'][0]}, y={self.state['pos'][1]}, rot={self.state['rot']}°")

    # Posición inicial en formación
    def formacion(self, index):
        if index < 15:
            fila = index
            num_fila = 15
            y = CENTER_Y_ARRIBA
        else:
            fila = index - 15
            num_fila = 15
            y = CENTER_Y_ABAJO

        total_width = (num_fila - 1) * HORIZONTAL_SPACING
        x = CENTER_X - total_width/2 + fila * HORIZONTAL_SPACING

        self.pos_inicial = [x, y]
        self.state["pos"] = self.pos_inicial[:]

        # Teletransportar al dispatcher
        if self.sock_send and self.udp_send_port:
            packet = {
                "src": self.robot_id,
                "type": "cmd",
                "cmd": "teleport",
                "data": {"x": x, "y": y, "rot": 90 if index < 15 else 270},
                "ts": int(time.time()*1000)
            }
            try:
                self.sock_send.sendto(json.dumps(packet).encode(), ("127.0.0.1", self.udp_send_port))
            except Exception as e:
                print(f"[{self.robot_id}] ERROR al enviar teleport UDP: {e}")

        # Ajustar rotación inicial
        self.state["rot"] = 90 if index < 15 else 270

    # Coreografía
    def coreografia(self, index, fila_arriba, fila_abajo):
        self.formacion(index)
        while True:
            if self.estado == STATE_INICIAL:
                self.estado = STATE_GIRAR

            elif self.estado == STATE_GIRAR:
                self.estado = STATE_AVANZAR

            elif self.estado == STATE_AVANZAR:
                if index < 15:
                    min_y = min(r.state["pos"][1] for r in fila_abajo)
                    if self.state["pos"][1] + SPEED < min_y - MIN_DIST:
                        self.state["pos"][1] += SPEED
                    else:
                        self.estado = STATE_RETROCEDER
                else:
                    max_y = max(r.state["pos"][1] for r in fila_arriba)
                    if self.state["pos"][1] - SPEED > max_y + MIN_DIST:
                        self.state["pos"][1] -= SPEED
                    else:
                        self.estado = STATE_RETROCEDER

            elif self.estado == STATE_RETROCEDER:
                dx = self.pos_inicial[0] - self.state["pos"][0]
                dy = self.pos_inicial[1] - self.state["pos"][1]
                dist = math.hypot(dx, dy)
                if dist > SPEED:
                    self.state["pos"][0] += SPEED * dx/dist
                    self.state["pos"][1] += SPEED * dy/dist
                else:
                    self.state["pos"] = self.pos_inicial[:]
                    self.estado = STATE_INICIAL

            time.sleep(0.05)

    # Iniciar robot
    def start(self, index, fila_arriba, fila_abajo):
        threading.Thread(target=self.send_state, daemon=True).start()
        threading.Thread(target=self.coreografia, args=(index,fila_arriba,fila_abajo), daemon=True).start()
        print(f"[{self.robot_id}] Robot iniciado")

# =====================================================
# Main
# =====================================================
robots = [Robot(f"ROB{i+1}") for i in range(NUM_ROBOTS)]
fila_arriba = robots[:15]
fila_abajo = robots[15:]

for idx, r in enumerate(robots):
    r.start(idx, fila_arriba, fila_abajo)

while True:
    time.sleep(1)
