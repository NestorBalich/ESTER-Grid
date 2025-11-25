# -*- coding: utf-8 -*-
# Ejemplo 1: Teletransportar (1 robot)
# Concepto: usar cmd "teleport" para saltar entre puntos

import socket, json, time

SIM_IP = "127.0.0.1"
SIM_PORT = 10009

class Robot:
    def __init__(self, robot_id="E1"):
        self.id = robot_id
        self.pos = [0.0, 0.0]
        self.rot = 0.0
        self.color = [255, 160, 80]
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

if __name__ == "__main__":
    r = Robot()
    # Algunos puntos alrededor del centro (450,300)
    puntos = [
        (450, 300, 0),   # centro
        (200, 150, 45),  # arriba-izq
        (700, 150, 135), # arriba-der
        (700, 450, 225), # abajo-der
        (200, 450, 315), # abajo-izq
        (450, 300, 0),   # vuelve al centro
    ]

    for (x, y, rot) in puntos:
        r.teleport(x, y, rot)
        time.sleep(0.6)