#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ejemplo TEST: Un solo robot con movimiento de latido
====================================================
Prueba simple para verificar la lógica de contracción/expansión.
Sin sincronización, solo 1 robot.
"""

import socket
import json
import time
import math

SIM_IP = "127.0.0.1"
SIM_PORT = 10009

# Configuración
MAX_CYCLES = 10  # 5 latidos completos
RADIO_MAX = 250  # Radio máximo (posición expandida)
RADIO_MIN = 150  # Radio mínimo (posición contraída)
RADIO_STEP = 2.0  # Cambio de radio por tick
TICK_RATE = 0.05  # 50ms por tick

def log(msg):
    """Imprime mensaje con timestamp"""
    t = time.time()
    mins = int(t / 60) % 60
    secs = int(t) % 60
    millis = int((t % 1) * 1000)
    print(f"{mins:02d}:{secs:02d}.{millis:03d}: {msg}", flush=True)


class RobotTest:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.pos = [0.0, 0.0]
        self.rot = 0.0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def teleport(self, x, y, rot):
        """Teleporta el robot a una posición específica"""
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
                "color": [255, 100, 100]
            }
        }
        msg = json.dumps(packet).encode('utf-8')
        self.sock.sendto(msg, (SIM_IP, SIM_PORT))
        time.sleep(0.1)

    def send_state(self):
        packet = {
            "type": "state",
            "src": self.robot_id,
            "name": self.robot_id,
            "data": {
                "pos": [self.pos[0], 0, self.pos[1]],
                "rot": self.rot,
                "color": [255, 100, 100]
            }
        }
        msg = json.dumps(packet).encode('utf-8')
        try:
            self.sock.sendto(msg, (SIM_IP, SIM_PORT))
        except Exception as e:
            log(f"Error enviando estado: {e}")

    def movimiento_latido(self):
        """
        Movimiento radial simple: contrae → expande → repite
        """
        # Centro del campo
        centro_x = 300
        centro_y = 300
        
        # Posición angular fija (arriba)
        angulo_posicion = -math.pi / 2  # -90° = arriba
        
        # Teleport inicial a posición expandida
        x_inicial = centro_x + RADIO_MAX * math.cos(angulo_posicion)
        y_inicial = centro_y + RADIO_MAX * math.sin(angulo_posicion)
        self.teleport(x_inicial, y_inicial, 0)
        log(f"📍 Robot teleportado a ({x_inicial:.0f}, {y_inicial:.0f})")
        
        # Estado inicial
        radio_actual = RADIO_MAX
        expandiendo = False  # Empieza contrayendo
        ciclos_completados = 0
        
        # Rotación propia
        angulo_rotacion = 0.0
        step_rotacion = 0.05
        
        log(f"🤖 {self.robot_id} iniciado en radio {radio_actual:.0f}")
        log(f"   Centro: ({centro_x}, {centro_y})")
        log(f"   Ángulo posición: {angulo_posicion * 180 / math.pi:.0f}°")
        log("")
        
        tick = 0
        while ciclos_completados < MAX_CYCLES:
            tick += 1
            
            # Actualizar radio (latido)
            if expandiendo:
                radio_actual += RADIO_STEP
                if radio_actual >= RADIO_MAX:
                    radio_actual = RADIO_MAX
                    expandiendo = False
                    ciclos_completados += 1
                    log(f"💓 Ciclo {ciclos_completados}/{MAX_CYCLES} completado - Radio MAX alcanzado ({radio_actual:.0f})")
            else:
                # Contrayendo
                radio_actual -= RADIO_STEP
                if radio_actual <= RADIO_MIN:
                    radio_actual = RADIO_MIN
                    expandiendo = True
                    log(f"💓 Radio MIN alcanzado ({radio_actual:.0f}) - Iniciando expansión (ciclo {ciclos_completados + 1})")
            
            # Calcular posición
            self.pos[0] = centro_x + radio_actual * math.cos(angulo_posicion)
            self.pos[1] = centro_y + radio_actual * math.sin(angulo_posicion)
            
            # Rotación propia
            angulo_rotacion += step_rotacion
            self.rot = angulo_rotacion * 180 / math.pi
            
            # Debug cada 50 ticks
            if tick % 50 == 0:
                dist_centro = math.sqrt((self.pos[0] - centro_x)**2 + (self.pos[1] - centro_y)**2)
                fase = "EXPANDIR ↗️" if expandiendo else "CONTRAER ↘️"
                log(f"🔍 Tick {tick:4d} | {fase} | radio={radio_actual:5.1f} | pos=({self.pos[0]:5.1f},{self.pos[1]:5.1f}) | dist={dist_centro:5.1f}")
            
            self.send_state()
            time.sleep(TICK_RATE)
        
        log("")
        log(f"✅ {self.robot_id} completó {MAX_CYCLES} ciclos")
        log(f"   Ticks totales: {tick}")
        log(f"   Radio final: {radio_actual:.0f}")


if __name__ == "__main__":
    log("=" * 60)
    log("EJEMPLO TEST: Robot con latido (1 solo robot)")
    log("=" * 60)
    log("🧪 Prueba: teletransportes en línea recta hacia el centro")
    log("")
    
    robot = RobotTest("TEST1")
    
    # Posición inicial: arriba del centro
    pos_inicial_x = 450  # Centro X del canvas (900/2)
    pos_inicial_y = 400 - RADIO_MAX  # 300 - 250 = 50 (arriba)
    
    # Centro
    centro_x = 450
    centro_y = 300
    
    log(f"Posición inicial: ({pos_inicial_x}, {pos_inicial_y})")
    log(f"Centro objetivo: ({centro_x}, {centro_y})")
    log("")
    
    # Teleport a posición inicial
    robot.teleport(pos_inicial_x, pos_inicial_y, 0)
    time.sleep(1)
    
    log("💓 Iniciando 10 ciclos de contracción/expansión...")
    log("")
    
    num_puntos = 20  # Más puntos = desplazamiento más largo
    punto_retorno = 15  # Punto de retorno (75% del camino hacia el centro)
    
    for ciclo in range(1, 11):  # 10 ciclos
        log(f"🔹 Ciclo {ciclo}/10 - CONTRAER (hasta punto {punto_retorno})")
        # Ir hacia el centro SOLO hasta el punto 7
        for i in range(punto_retorno + 1):
            t = i / num_puntos
            x = pos_inicial_x + t * (centro_x - pos_inicial_x)
            y = pos_inicial_y + t * (centro_y - pos_inicial_y)
            
            # Actualizar posición y rotación
            robot.pos[0] = x
            robot.pos[1] = y
            robot.rot += 5  # Rotar 5 grados por paso
            robot.send_state()
            time.sleep(0.05)
        
        log(f"   ✅ Punto {punto_retorno} alcanzado")
        time.sleep(0.2)
        
        log(f"🔹 Ciclo {ciclo}/10 - EXPANDIR (de vuelta a inicial)")
        # Regresar desde punto 7 a posición inicial
        for i in range(punto_retorno, -1, -1):  # 7,6,5,4,3,2,1,0
            t = i / num_puntos
            x = pos_inicial_x + t * (centro_x - pos_inicial_x)
            y = pos_inicial_y + t * (centro_y - pos_inicial_y)
            
            # Actualizar posición y rotación
            robot.pos[0] = x
            robot.pos[1] = y
            robot.rot += 5  # Seguir rotando
            robot.send_state()
            time.sleep(0.05)
        
        log(f"   ✅ Posición inicial alcanzada")
        time.sleep(0.2)
        log("")
    
    log("=" * 60)
    log("✅ Test completado - 10 latidos (75% del recorrido)!")
    log("=" * 60)
