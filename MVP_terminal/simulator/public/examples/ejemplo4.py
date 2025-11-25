"""Ejemplo 4: Mover dos robots.

Dos robots (R1 y R2) se mueven con trayectorias simples:
 - R1 recorre un rectángulo.
 - R2 realiza movimiento sinusoidal horizontal mientras avanza verticalmente.

Cada estado se envía al simulador para visualizarlo. Este ejemplo
no usa gemelos ni mensajes; solo muestra movimiento básico coordinado.
"""

import socket
import json
import time
import math

SIM_IP = "127.0.0.1"
SIM_PORT = 10009

TICK = 0.05  # 50ms
STEPS_RECT = 40

class Robot:
    def __init__(self, robot_id, x, y, color):
        self.robot_id = robot_id
        self.x = x
        self.y = y
        self.rot = 0
        self.color = color
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_state(self):
        pkt = {
            "type": "state",
            "src": self.robot_id,
            "name": self.robot_id,
            "data": {
                "pos": [self.x, 0, self.y],
                "rot": self.rot,
                "color": self.color
            }
        }
        self.sock.sendto(json.dumps(pkt).encode('utf-8'), (SIM_IP, SIM_PORT))

    def teleport(self, x, y, rot=0):
        self.x = x
        self.y = y
        self.rot = rot
        pkt = {
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
        self.sock.sendto(json.dumps(pkt).encode('utf-8'), (SIM_IP, SIM_PORT))


def mover_rectangulo(r: Robot, ancho=160, alto=120):
    """Avanza en un rectángulo usando 4 tramos."""
    # Cada lado dividido en STEPS_RECT pasos
    # Lado superior (derecha)
    for i in range(STEPS_RECT):
        r.x += ancho / STEPS_RECT
        r.rot = 0
        r.send_state(); time.sleep(TICK)
    # Lado derecho (abajo)
    for i in range(STEPS_RECT):
        r.y += alto / STEPS_RECT
        r.rot = 90
        r.send_state(); time.sleep(TICK)
    # Lado inferior (izquierda)
    for i in range(STEPS_RECT):
        r.x -= ancho / STEPS_RECT
        r.rot = 180
        r.send_state(); time.sleep(TICK)
    # Lado izquierdo (arriba)
    for i in range(STEPS_RECT):
        r.y -= alto / STEPS_RECT
        r.rot = 270
        r.send_state(); time.sleep(TICK)


def mover_sinusoidal(r: Robot, avance=240, amp=40):
    """Movimiento sinusoidal en X mientras avanza hacia abajo."""
    pasos = int(avance / 2)
    for i in range(pasos):
        fase = i / 12.0
        r.y += 2
        r.x += math.sin(fase) * (amp / pasos * 6)  # escala suave
        r.rot = (90 + math.sin(fase)*30) % 360  # inclinación leve
        r.send_state(); time.sleep(TICK)


if __name__ == "__main__":
    print("Iniciando ejemplo 4: Mover dos robots")
    r1 = Robot("R1", 180, 180, [255,120,120])
    r2 = Robot("R2", 500, 160, [120,160,255])

    r1.teleport(r1.x, r1.y, 0)
    r2.teleport(r2.x, r2.y, 90)
    time.sleep(0.5)

    # Ejecutar trayectorias intercaladas para sensación de simultáneo
    for ciclo in range(2):
        print(f"Ciclo {ciclo+1}/2")
        mover_rectangulo(r1)
        mover_sinusoidal(r2)

    print("Ejemplo 4 completado.")