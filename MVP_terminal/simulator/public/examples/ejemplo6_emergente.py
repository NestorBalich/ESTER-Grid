# -*- coding: utf-8 -*-
# =====================================================
# Ejemplo 6: Formación Doble + Líder (30 + 1 robots)
# =====================================================
# Posiciona 30 robots en dos filas iguales: R1..R15 arriba,
# R16..R30 abajo, todos teletransportados y estáticos, más un
# robot adicional "LEADER" (naranja) centrado para referencia.
# =====================================================

import socket
import json
import time
import threading
import math

SIM_IP = "127.0.0.1"
SIM_PORT = 10009  # simulador (recibe estados)

DISP_IP = "127.0.0.1"
DISP_MSG_PORT = 10011  # dispatcher (router de mensajes)

WINDOW_W = 900
WINDOW_H = 600
CENTER_X = WINDOW_W//2
CENTER_Y = WINDOW_H//2

NUM_ROBOTS = 30
SPACING = 30  # Separación entre robots en la formación

class Robot:
    def __init__(self, robot_id, start_pos, start_rot=0, color=None):
        self.robot_id = robot_id
        self.pos = [start_pos[0], start_pos[1]]
        self.rot = start_rot
        self.color = color or [200, 200, 200]
        # Sockets
        self.sock_state = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_msg = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_msg.settimeout(0.05)
        self.running = True

    def send_state(self):
        packet = {
            "type": "state",
            "src": self.robot_id,
            "name": self.robot_id,
            "data": {
                "pos": [self.pos[0], 0, self.pos[1]],
                "rot": self.rot,
                "color": self.color
            }
        }
        self.sock_state.sendto(json.dumps(packet).encode('utf-8'), (SIM_IP, SIM_PORT))

    def teleport(self, x, y, rot):
        self.pos = [x, y]
        self.rot = rot
        packet = {
            "type": "state",
            "src": self.robot_id,
            "name": self.robot_id,
            "cmd": "teleport",
            "cmdData": {"x": x, "y": y, "rot": rot},
            "data": {
                "pos": [x, 0, y],
                "rot": rot,
                "color": self.color
            }
        }
        self.sock_state.sendto(json.dumps(packet).encode('utf-8'), (SIM_IP, SIM_PORT))

    def register(self):
        pkt = {"type": "register", "src": self.robot_id}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def send_msg(self, to, data):
        mid = f"{self.robot_id}_{int(time.time()*1000)}"
        pkt = {"type": "msg", "src": self.robot_id, "to": to, "mid": mid, "data": data}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def broadcast(self, data):
        pkt = {"type": "broadcast", "src": self.robot_id, "data": data}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def recv_any(self):
        try:
            data, _ = self.sock_msg.recvfrom(4096)
            pkt = json.loads(data.decode('utf-8'))
            return pkt
        except socket.timeout:
            return None

    def move_towards(self, tx, ty, step_px=3.0):
        dx = tx - self.pos[0]
        dy = ty - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist < 0.01:
            return True
        k = min(step_px, dist) / (dist if dist > 0 else 1)
        self.pos[0] += dx * k
        self.pos[1] += dy * k
        self.rot = (math.degrees(math.atan2(dy, dx)) + 360) % 360
        self.send_state()
        return False

# (Se removió lógica de líder/seguidores; este ejemplo ahora sólo posiciona.)


if __name__ == "__main__":
    print("=" * 60)
    print("Ejemplo 6: 2 Filas de 15 Robots + Líder")
    print("=" * 60)
    print("Posicionando R1..R15 (fila superior), R16..R30 (fila inferior) y LEADER centrado.")
    print("=" * 60)

    robots = []

    top_count = 15
    bottom_count = 15
    spacing_x = 40
    vertical_gap = 60
    bottom_margin = 70

    # Línea inferior (R16..R30)
    start_bottom_x = CENTER_X - (bottom_count - 1) * spacing_x / 2
    y_bottom = WINDOW_H - bottom_margin
    for i in range(bottom_count):
        name = f"R{top_count + 1 + i}"  # R16..R30
        x = start_bottom_x + i * spacing_x
        rb = Robot(name, (x, y_bottom), 0, color=[100,200,240])
        rb.register()
        rb.teleport(x, y_bottom, 0)
        robots.append(rb)
        print(f"[{name}] fila inferior x={int(x)} y={int(y_bottom)}")
        time.sleep(0.02)

    # Línea superior (R1..R15) alineada sobre la inferior
    y_top = y_bottom - vertical_gap
    for i in range(top_count):
        name = f"R{i+1}"  # R1..R15
        x = start_bottom_x + i * spacing_x
        rb = Robot(name, (x, y_top), 0, color=[100,200,240])
        rb.register()
        rb.teleport(x, y_top, 0)
        robots.append(rb)
        print(f"[{name}] fila superior x={int(x)} y={int(y_top)}")
        time.sleep(0.02)

    # Añadir líder naranja centrado (encima del punto medio entre las dos filas)
    leader_y = y_top - 70  # un poco por encima de la fila superior
    leader = Robot("LEADER", (CENTER_X, leader_y), 0, color=[255,140,0])
    leader.register()
    leader.teleport(CENTER_X, leader_y, 0)
    robots.append(leader)
    print(f"[LEADER] centrado x={CENTER_X} y={int(leader_y)}")

    print("\n✔️ Formación completa: 2 filas de 15 robots + líder")
    print("Presiona Ctrl+C para terminar\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✔️ Ejemplo 6 finalizado")
