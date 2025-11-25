# -*- coding: utf-8 -*-
# =====================================================
# Ejemplo 10: Robot Seguidor (Leader-Follower)
# =====================================================
# Robot A (líder) se mueve en un patrón (espiral) y envía
# su posición constantemente al robot B via dispatcher.
# Robot B (seguidor) recibe las coordenadas y sigue al líder
# manteniéndose a cierta distancia.
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

# ----------------------------
# Robot A: Líder (mueve en espiral y transmite posición)
# ----------------------------

def robot_leader_thread():
    A = Robot("LEADER", (CENTER_X, CENTER_Y), 0, color=[240, 100, 100])
    A.register()
    A.teleport(A.pos[0], A.pos[1], A.rot)
    time.sleep(0.5)

    print("[LEADER] iniciando movimiento en espiral...")

    # Parámetros de espiral
    angle = 0.0
    radius = 20.0
    radius_step = 2.0  # crece el radio
    angle_step = 0.15  # velocidad angular

    for _ in range(200):  # 200 pasos
        # Calcular nueva posición en espiral
        x = CENTER_X + radius * math.cos(angle)
        y = CENTER_Y + radius * math.sin(angle)
        
        # Moverse hacia esa posición
        A.pos[0] = x
        A.pos[1] = y
        A.rot = (math.degrees(angle) + 90) % 360  # orientación tangencial
        A.send_state()

        # Enviar posición al seguidor
        A.send_msg("FOLLOWER", {"cmd": "follow", "pos": [x, y]})

        # Incrementar espiral
        angle += angle_step
        radius += radius_step

        time.sleep(0.05)

    print("[LEADER] movimiento completado")

# ----------------------------
# Robot B: Seguidor (recibe posición del líder y lo sigue)
# ----------------------------

def robot_follower_thread():
    B = Robot("FOLLOWER", (CENTER_X - 100, CENTER_Y - 100), 0, color=[100, 240, 100])
    B.register()
    B.teleport(B.pos[0], B.pos[1], B.rot)

    print("[FOLLOWER] esperando órdenes del líder...")

    target_pos = None
    last_update = time.time()

    while True:
        # Recibir mensajes del líder
        pkt = B.recv_any()
        if pkt and pkt.get('type') == 'msg' and pkt.get('src') == 'LEADER':
            data = pkt.get('data', {})
            if data.get('cmd') == 'follow' and data.get('pos'):
                target_pos = data['pos']
                last_update = time.time()

        # Si tenemos una posición objetivo, seguir
        if target_pos:
            # Mantener distancia mínima de 50px
            dx = target_pos[0] - B.pos[0]
            dy = target_pos[1] - B.pos[1]
            dist = math.hypot(dx, dy)
            
            if dist > 50:  # solo moverse si está lejos
                B.move_towards(target_pos[0], target_pos[1], step_px=4.0)
            else:
                # Ya está cerca, solo actualizar rotación hacia el líder
                B.rot = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                B.send_state()

        # Si no recibe actualizaciones en 3s, detenerse
        if time.time() - last_update > 3.0:
            break

        time.sleep(0.02)

    print("[FOLLOWER] líder detenido, terminando seguimiento")


if __name__ == "__main__":
    print("=" * 60)
    print("Ejemplo 10: Robot Seguidor (Leader-Follower)")
    print("=" * 60)
    print("El robot LEADER se mueve en espiral y transmite")
    print("su posición. FOLLOWER lo sigue manteniendo distancia.")
    print("=" * 60)

    thA = threading.Thread(target=robot_leader_thread, daemon=True)
    thB = threading.Thread(target=robot_follower_thread, daemon=True)
    
    thB.start()
    time.sleep(0.3)  # dar tiempo a B para registrarse
    thA.start()

    # Esperar a que terminen
    thA.join()
    thB.join()
    
    time.sleep(1)
    print("✔️ Ejemplo 10 finalizado")
