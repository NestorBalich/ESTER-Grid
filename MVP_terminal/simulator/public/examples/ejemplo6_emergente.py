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
SPACING = 30  # separación base entre robots
FOLLOW_SPACING = 40  # distancia objetivo entre cada segmento de la serpiente
MIN_DIST = 30        # distancia mínima para evitar choques

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
        self.last_state_time = time.time()

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
        self.last_state_time = time.time()

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
        self.last_state_time = time.time()

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

    def start_keepalive(self, interval=3.0):
        def loop():
            while self.running:
                now = time.time()
                # Enviar estado si han pasado > intervalo o si no hubo movimiento reciente
                if now - self.last_state_time >= interval:
                    self.send_state()
                time.sleep(0.5)
        th = threading.Thread(target=loop, daemon=True)
        th.start()

# (Se removió lógica de líder/seguidores; este ejemplo ahora sólo posiciona.)


if __name__ == "__main__":
    print("=" * 60)
    print("Ejemplo 6: 2 Filas de 15 Robots + Líder")
    print("=" * 60)
    print("Posicionando R1..R15 (fila superior), R16..R30 (fila inferior) y LEADER centrado.")
    print("=" * 60)

    robots = []

    # Formación original: dos filas de 15 (superior R1..R15, inferior R16..R30)
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

    # Añadir líder naranja centrado encima de la fila superior
    leader_y = y_top - 70  # un poco por encima de la fila superior
    leader = Robot("LEADER", (CENTER_X, leader_y), 0, color=[255,140,0])
    leader.register()
    leader.teleport(CENTER_X, leader_y, 0)
    robots.append(leader)
    print(f"[LEADER] centrado x={CENTER_X} y={int(leader_y)}")

    # =============================
    # Comportamiento: Formación tipo tren (mantiene estructura de dos filas)
    # =============================

    # Mapa rápido id -> objeto
    robot_map = {r.robot_id: r for r in robots}
    
    # Guardar offsets relativos iniciales de cada robot respecto al líder
    initial_offsets = {}
    for r in robots:
        if r.robot_id != "LEADER":
            initial_offsets[r.robot_id] = (
                r.pos[0] - leader.pos[0],
                r.pos[1] - leader.pos[1]
            )

    def leader_path_formation():
        """LEADER recorre el perímetro y broadcast su posición a todos los robots."""
        margin = 40
        speed = 4.0
        perimeter = [
            (margin, margin),
            (WINDOW_W - margin, margin),
            (WINDOW_W - margin, WINDOW_H - margin),
            (margin, WINDOW_H - margin)
        ]
        # Dar dos vueltas completas
        for lap in range(2):
            print(f"[LEADER] iniciando vuelta {lap + 1}/2")
            for (tx, ty) in perimeter:
                while math.hypot(leader.pos[0] - tx, leader.pos[1] - ty) > 6:
                    leader.move_towards(tx, ty, step_px=speed)
                    # Broadcast posición a todos
                    leader.broadcast({"pos": leader.pos[:], "rot": leader.rot})
                    time.sleep(0.015)
        # Regresar al centro final
        while math.hypot(leader.pos[0] - CENTER_X, leader.pos[1] - leader_y) > 6:
            leader.move_towards(CENTER_X, leader_y, step_px=3.5)
            leader.broadcast({"pos": leader.pos[:], "rot": leader.rot})
            time.sleep(0.015)
        leader.broadcast({"done": True})
        print("[LEADER] recorrido completo (2 vueltas)")

    def formation_follower(follower_id: str, offset_x: float, offset_y: float):
        """Mantiene posición relativa fija respecto al líder."""
        rb = robot_map.get(follower_id)
        if not rb:
            print(f"[FORM] {follower_id} no encontrado")
            return
        done = False
        while not done:
            pkt = rb.recv_any()
            if pkt and pkt.get("type") == "broadcast" and pkt.get("src") == "LEADER":
                data = pkt.get("data", {})
                if data.get("done"):
                    done = True
                    break
                if "pos" in data:
                    leader_pos = data["pos"]
                    # Calcular posición objetivo: líder + offset inicial
                    target_x = leader_pos[0] + offset_x
                    target_y = leader_pos[1] + offset_y
                    
                    # Mover hacia la posición objetivo suavemente
                    dx = target_x - rb.pos[0]
                    dy = target_y - rb.pos[1]
                    dist = math.hypot(dx, dy)
                    if dist > 2:  # umbral mínimo para evitar jitter
                        step = min(3.0, dist * 0.5)  # paso proporcional a distancia
                        rb.pos[0] += (dx / dist) * step
                        rb.pos[1] += (dy / dist) * step
                        rb.rot = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                        rb.send_state()
            time.sleep(0.01)
        print(f"[{follower_id}] formación terminada")

    # Iniciar heartbeat (keepalive) para todos los robots para evitar timeout
    for r in robots:
        r.start_keepalive(interval=3.0)  # cada ~3s asegura actividad

    # Crear hilos de formación para R1..R30 (cada uno mantiene offset respecto al líder)
    formation_threads = []
    for robot_id, (offset_x, offset_y) in initial_offsets.items():
        th = threading.Thread(target=formation_follower, args=(robot_id, offset_x, offset_y), daemon=True)
        formation_threads.append(th)
    
    # Lanzar seguidores primero
    for th in formation_threads:
        th.start()
    time.sleep(0.3)
    
    # Lanzar líder
    th_leader = threading.Thread(target=leader_path_formation, daemon=True)
    th_leader.start()

    print("\n✔️ Formación tipo tren iniciada (2 filas mantienen estructura siguiendo al líder)")
    print("Esperando finalización del recorrido del líder...")

    th_leader.join()
    time.sleep(2.0)
    # Detener keepalive
    for r in robots:
        r.running = False
    print("\n✔️ Ejemplo 6 finalizado")
