# -*- coding: utf-8 -*-
# Ejemplo 2: Girar y avanzar (1 robot)
# Concepto: integrar posición con heading (rotación) y velocidad

import socket, json, time, math

SIM_IP = "127.0.0.1"
SIM_PORT = 10009
TICK_RATE = 0.02
SPEED = 3.0  # píxeles por tick

class Robot:
    def __init__(self, robot_id="E2"):
        self.id = robot_id
        self.pos = [0.0, 0.0]
        self.rot = 0.0  # grados
        self.color = [120, 255, 120]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def teleport(self, x, y, rot=0):
        self.pos = [x, y]
        self.rot = rot
        pkt = {
            "type": "state",
            "src": self.id,
            "name": self.id,
            "cmd": "teleport",
            "cmdData": {"x": x, "y": y, "rot": rot},
            "data": {"pos": [x, 0, y], "rot": rot, "color": self.color},
        }
        self.sock.sendto(json.dumps(pkt).encode(), (SIM_IP, SIM_PORT))

    def send(self):
        pkt = {
            "type": "state",
            "src": self.id,
            "name": self.id,
            "data": {"pos": [self.pos[0], 0, self.pos[1]], "rot": self.rot, "color": self.color},
        }
        self.sock.sendto(json.dumps(pkt).encode(), (SIM_IP, SIM_PORT))

if __name__ == "__main__":
    r = Robot()
    # Posición inicial a la izquierda
    r.teleport(120, 300, 0)
    time.sleep(0.3)

    # Avanza mientras gira suavemente
    pasos = 500
    for _ in range(pasos):
        # Avanza en dirección de rotación actual
        rad = math.radians(r.rot)
        r.pos[0] += SPEED * math.cos(rad)
        r.pos[1] += SPEED * math.sin(rad)
        # Gira un poco cada tick
        r.rot = (r.rot + 2) % 360
        r.send()
        time.sleep(TICK_RATE)

    # Teleport final al centro
    r.teleport(450, 300, r.rot)