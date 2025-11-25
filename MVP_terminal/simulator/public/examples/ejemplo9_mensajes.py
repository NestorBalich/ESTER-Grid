# -*- coding: utf-8 -*-
# =====================================================
# Ejemplo 9: Mensajería directa vía Dispatcher (request/response)
# =====================================================
# Dos robots (A y B) se registran en el dispatcher y
# se envían mensajes entre sí para coordinar una acción.
# Flujo:
#  1) Ambos se registran en el router de mensajes
#  2) A pregunta "ready?" a B y espera respuesta
#  3) A envía "go"; ambos avanzan hacia el centro sincronizados
#  4) Al llegar, A envía "done", B responde "ack"
# El estado (posición/rotación) se reporta al simulador por UDP.
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
    def __init__(self, robot_id, start_pos, start_rot=0):
        self.robot_id = robot_id
        self.pos = [start_pos[0], start_pos[1]]
        self.rot = start_rot
        self.color = [200, 240, 120] if robot_id.endswith('A') else [120, 200, 240]
        # Sockets
        self.sock_state = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_msg = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_msg.settimeout(0.1)  # lectura no bloqueante con timeout corto
        self.running = True

    # -------------
    # Simulador (estado)
    # -------------
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
    
    def spin(self, seconds=1.0, step_deg=18, color=None):
        """Girar en el lugar enviando estado para que se note la espera."""
        end_time = time.time() + seconds
        old_color = list(self.color)
        if color is not None:
            self.color = color
        while time.time() < end_time:
            self.rot = (self.rot + step_deg) % 360
            self.send_state()
            time.sleep(0.02)
        if color is not None:
            self.color = old_color
            self.send_state()

    # -------------
    # Dispatcher (mensajes)
    # -------------
    def register(self):
        pkt = {"type": "register", "src": self.robot_id}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def send_msg(self, to, mid, data):
        pkt = {"type": "msg", "src": self.robot_id, "to": to, "mid": mid, "data": data}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def send_reply(self, to, mid, data):
        pkt = {"type": "reply", "src": self.robot_id, "to": to, "mid": mid, "data": data}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def recv_any(self):
        try:
            data, _ = self.sock_msg.recvfrom(4096)
            pkt = json.loads(data.decode('utf-8'))
            return pkt
        except socket.timeout:
            return None

    # -------------
    # Movimiento simple
    # -------------
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
# Coordinación
# ----------------------------

def robot_A_thread():
    A = Robot("R1A", (CENTER_X - 200, CENTER_Y), 0)
    A.register()
    A.teleport(A.pos[0], A.pos[1], A.rot)

    # esperar unos milisegundos para que B registre
    time.sleep(0.3)

    # 1) Ping/Pong de preparación
    mid = f"ready_{int(time.time()*1000)}"
    A.send_msg("R2B", mid, {"q": "ready?"})
    print("[A] enviado 'ready?' a B")

    t0 = time.time()
    t_print = time.time()
    ready = False
    while time.time() - t0 < 5.0 and not ready:
        pkt = A.recv_any()
        if pkt and pkt.get('type') == 'reply' and pkt.get('mid') == mid:
            print("[A] respuesta de B:", pkt.get('data'))
            ready = True
        if time.time() - t_print > 0.25 and not ready:
            print("[A] \u23f3 esperando respuesta de B...")
            t_print = time.time()
        time.sleep(0.02)

    if not ready:
        print("[A] B no respondió a tiempo; saliendo")
        return

    # 2) Mostrar espera visible antes de la orden (spin + color)
    print("[A] listo para avanzar; realizando una breve espera visible...")
    A.spin(seconds=1.2, step_deg=24, color=[255, 200, 80])

    # 3) Orden de avance sincronizado
    go_mid = f"go_{int(time.time()*1000)}"
    A.send_msg("R2B", go_mid, {"cmd": "go", "target": [CENTER_X, CENTER_Y]})
    print("[A] enviado 'go' a B; A comienza a moverse al centro")

    # A también avanza al centro
    while not A.move_towards(CENTER_X, CENTER_Y):
        time.sleep(0.02)

    print("[A] llegó al centro")

    # 4) Finalización
    done_mid = f"done_{int(time.time()*1000)}"
    A.send_msg("R2B", done_mid, {"status": "A_arrived"})
    print("[A] esperando ack final de B...")
    # esperar ack opcional (timeout 5s para los 3s de delay de B)
    t0 = time.time()
    t_print = time.time()
    while time.time() - t0 < 5.0:
        pkt = A.recv_any()
        if pkt and pkt.get('type') == 'reply' and pkt.get('mid') == done_mid:
            print("[A] B ack final:", pkt.get('data'))
            break
        if time.time() - t_print > 0.25:
            print("[A] \u23f3 esperando ack final de B...")
            t_print = time.time()
        time.sleep(0.02)


def robot_B_thread():
    B = Robot("R2B", (CENTER_X + 200, CENTER_Y), 180)
    B.register()
    B.teleport(B.pos[0], B.pos[1], B.rot)

    arrived = False
    while True:
        pkt = B.recv_any()
        if not pkt:
            # actualizar si en movimiento
            if arrived:
                break
            time.sleep(0.02)
            continue

        t = pkt.get('type')
        src = pkt.get('src')
        mid = pkt.get('mid')
        data = pkt.get('data', {})

        if t == 'msg' and src == 'R1A' and data.get('q') == 'ready?':
            # responder listo (demora intencional de 3s para que A espere visiblemente)
            time.sleep(3.0)
            B.send_reply('R1A', mid, {"ans": "ready"})
            print("[B] respondió 'ready' a A")

        elif t == 'msg' and src == 'R1A' and data.get('cmd') == 'go':
            target = data.get('target', [CENTER_X, CENTER_Y])
            print("[B] recibido 'go' de A; procesando (delay 3s)...")
            # delay de 3s antes de responder y moverse
            time.sleep(3.0)
            print("[B] B avanza al centro")
            # pequeña espera visible antes de moverse
            B.spin(seconds=0.6, step_deg=24, color=[255, 120, 120])
            # mover hasta el centro
            while not B.move_towards(target[0], target[1]):
                time.sleep(0.02)
            arrived = True
            # enviar ack con delay de 3s
            time.sleep(3.0)
            B.send_reply('R1A', mid, {"status": "B_arrived"})
            print("[B] llegó al centro y envió ack")

    print("[B] terminado")


if __name__ == "__main__":
    print("==============================================")
    print("Ejemplo 9: Mensajería directa con Dispatcher")
    print("==============================================")
    print("Iniciando robots A y B...")

    thA = threading.Thread(target=robot_A_thread, daemon=True)
    thB = threading.Thread(target=robot_B_thread, daemon=True)
    thA.start(); thB.start()

    # Esperar a que terminen (máximo 10s)
    t0 = time.time()
    while time.time() - t0 < 10.0:
        time.sleep(0.1)
    print("✔️ Ejemplo 9 finalizado")
