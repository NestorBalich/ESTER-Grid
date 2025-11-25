# -*- coding: utf-8 -*-
# =====================================================
# Ejemplo 6: Formación de 30 robots en dos filas
# Descripción: Dos filas de 15 robots que se mueven
#              de forma sincronizada y se aproximan
# =====================================================

import socket
import json
import time
import threading
import random
import math
from datetime import datetime

# Configuración del simulador
SIM_IP = "127.0.0.1"
SIM_PORT = 10009

NUM_ROBOTS = 30
SPEED = 2.0
MIN_DIST = 60  # distancia mínima entre filas (aumentada para menos choques)
MAX_CYCLES = 3  # número de ciclos antes de terminar
TICK_RATE = 0.05  # tiempo entre actualizaciones (50ms)

# Estados de movimiento
STATE_INICIAL = 0
STATE_AVANZAR = 1
STATE_RETROCEDER = 2
STATE_FINALIZADO = 3

# Sincronización global
tick_lock = threading.Lock()
tick_event = threading.Event()

def log(msg):
    """Imprime mensaje (el timestamp lo agrega el backend)"""
    print(msg)

# Formación
CENTER_X = 450
CENTER_Y_ARRIBA = 150
CENTER_Y_ABAJO = 450
HORIZONTAL_SPACING = 30  # separación horizontal entre robots

class Robot:
    def __init__(self, robot_id, index):
        self.robot_id = robot_id
        self.index = index
        self.color = [random.randint(80, 255), random.randint(80, 255), random.randint(80, 255)]
        self.pos = [0, 0]
        self.rot = 0
        self.pos_inicial = [0, 0]
        self.estado = STATE_INICIAL
        self.ciclos_completados = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def send_state(self):
        """Envía el estado actual del robot al simulador"""
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
        msg = json.dumps(packet).encode('utf-8')
        self.sock.sendto(msg, (SIM_IP, SIM_PORT))

    def teleport(self, x, y, rot):
        """Teletransporta el robot a una posición"""
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
        msg = json.dumps(packet).encode('utf-8')
        self.sock.sendto(msg, (SIM_IP, SIM_PORT))

    def set_formacion(self):
        """Coloca el robot en su posición inicial de formación"""
        if self.index < 15:  # Fila de arriba
            fila = self.index
            num_fila = 15
            y = CENTER_Y_ARRIBA
            self.rot = 90  # Mirando hacia abajo
        else:  # Fila de abajo
            fila = self.index - 15
            num_fila = 15
            y = CENTER_Y_ABAJO
            self.rot = 270  # Mirando hacia arriba

        total_width = (num_fila - 1) * HORIZONTAL_SPACING
        x = CENTER_X - total_width/2 + fila * HORIZONTAL_SPACING

        self.pos_inicial = [x, y]
        self.teleport(x, y, self.rot)

    def coreografia(self, fila_arriba, fila_abajo):
        """Ejecuta la coreografía de movimiento (sincronizada por ticks)"""
        while self.estado != STATE_FINALIZADO:
            # Esperar al próximo tick global
            tick_event.wait()
            
            if self.estado == STATE_INICIAL:
                self.estado = STATE_AVANZAR

            elif self.estado == STATE_AVANZAR:
                # Fila superior se mueve hacia abajo
                if self.index < 15:
                    robots_activos = [r for r in fila_abajo if r.estado != STATE_FINALIZADO]
                    if robots_activos:
                        min_y = min(r.pos[1] for r in robots_activos)
                        if self.pos[1] + SPEED < min_y - MIN_DIST:
                            self.pos[1] += SPEED
                        else:
                            self.estado = STATE_RETROCEDER
                    else:
                        self.estado = STATE_RETROCEDER
                # Fila inferior se mueve hacia arriba
                else:
                    robots_activos = [r for r in fila_arriba if r.estado != STATE_FINALIZADO]
                    if robots_activos:
                        max_y = max(r.pos[1] for r in robots_activos)
                        if self.pos[1] - SPEED > max_y + MIN_DIST:
                            self.pos[1] -= SPEED
                        else:
                            self.estado = STATE_RETROCEDER
                    else:
                        self.estado = STATE_RETROCEDER

                # Desplazamiento lateral suave para espaciar (solo mientras AVANZAR)
                # Evita alineación perfecta que provoca choques frontales.
                wave_amp = 10  # píxeles de amplitud
                wave_speed = 0.8
                phase = (time.time() * wave_speed) + (self.index * 0.4)
                self.pos[0] = self.pos_inicial[0] + math.sin(phase) * wave_amp

            elif self.estado == STATE_RETROCEDER:
                # Volver a posición inicial
                dx = self.pos_inicial[0] - self.pos[0]
                dy = self.pos_inicial[1] - self.pos[1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > SPEED:
                    self.pos[0] += SPEED * dx/dist
                    self.pos[1] += SPEED * dy/dist
                else:
                    self.pos = self.pos_inicial[:]
                    self.ciclos_completados += 1
                    if self.ciclos_completados >= MAX_CYCLES:
                        self.estado = STATE_FINALIZADO
                    else:
                        self.estado = STATE_INICIAL

            self.send_state()

    def start(self, fila_arriba, fila_abajo):
        """Inicia el robot en su hilo de ejecución"""
        threading.Thread(target=self.coreografia, args=(fila_arriba, fila_abajo), daemon=True).start()


# =====================================================
# Main
# =====================================================
if __name__ == "__main__":
    log(f"Iniciando {NUM_ROBOTS} robots en formación de dos filas")
    print()
    
    # Crear robots
    robots = [Robot(f"ROB{i+1}", i) for i in range(NUM_ROBOTS)]
    fila_arriba = robots[:15]
    fila_abajo = robots[15:]

    # Colocar en formación inicial
    log("Colocando robots en formación inicial...")
    for r in robots:
        r.set_formacion()
        time.sleep(0.05)

    time.sleep(2)  # Esperar a que se posicionen

    # Iniciar coreografía
    log("Iniciando coreografía de movimiento...")
    for r in robots:
        r.start(fila_arriba, fila_abajo)

    log(f"Robots en movimiento. Ejecutarán {MAX_CYCLES} ciclos y terminarán.")
    print()
    
    # Bucle de sincronización global (maestro de ticks)
    ciclo_anterior = 0
    tick_count = 0
    
    while any(r.estado != STATE_FINALIZADO for r in robots):
        # Sincronizar: señalar a todos los robots que procesen un paso
        tick_event.set()
        time.sleep(TICK_RATE)
        tick_event.clear()
        
        tick_count += 1
        
        # Mostrar progreso cada cierto tiempo
        if tick_count % 20 == 0:  # cada ~1 segundo
            terminados = sum(1 for r in robots if r.estado == STATE_FINALIZADO)
            ciclo_actual = max(r.ciclos_completados for r in robots)
            
            if ciclo_actual > ciclo_anterior:
                log(f"✓ Ciclo {ciclo_actual}/{MAX_CYCLES} completado por algunos robots")
                ciclo_anterior = ciclo_actual
            
            if terminados > 0:
                activos = [r.robot_id for r in robots if r.estado != STATE_FINALIZADO]
                if len(activos) <= 5 and len(activos) > 0:
                    log(f"  Esperando a: {', '.join(activos)}")
    
    print(f"{'='*60}")
    log(f"¡Programa completado! Los {NUM_ROBOTS} robots completaron {MAX_CYCLES} ciclos.")
    print(f"{'='*60}")
