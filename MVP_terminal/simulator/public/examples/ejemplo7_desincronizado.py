# -*- coding: utf-8 -*-
# =====================================================
# Ejemplo 7: DESINCRONIZACIÓN (problema común)
# =====================================================
# Este ejemplo MUESTRA EL PROBLEMA de usar sleep() 
# independiente en cada robot. Con el tiempo, los robots
# se desincronizarán debido a pequeñas variaciones en
# el timing de cada thread.
# =====================================================

import socket
import json
import time
import threading
import random
import math

SIM_IP = "127.0.0.1"
SIM_PORT = 10009

NUM_ROBOTS = 20
SPEED = 3.0
MAX_CYCLES = 10  # MÁS CICLOS para que la desincronización sea evidente

def log(msg):
    print(msg)

class RobotDesincronizado:
    def __init__(self, robot_id, index):
        self.robot_id = robot_id
        self.index = index
        self.color = [random.randint(80, 255), random.randint(80, 255), random.randint(80, 255)]
        self.pos = [0, 0]
        self.rot = 0
        self.ciclos = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # ⚠️ PROBLEMA: Cada robot tiene su propio delay ligeramente diferente
        # Esto simula variaciones naturales de CPU/sistema
        self.delay = 0.05 + random.uniform(-0.005, 0.005)
        
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
        msg = json.dumps(packet).encode('utf-8')
        self.sock.sendto(msg, (SIM_IP, SIM_PORT))

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
        msg = json.dumps(packet).encode('utf-8')
        self.sock.sendto(msg, (SIM_IP, SIM_PORT))

    def movimiento_circular(self):
        """
        Cada robot se mueve en círculo INDEPENDIENTEMENTE.
        ⚠️ PROBLEMA: Usa sleep() individual, acumula errores de timing
        """
        # Posición en círculo
        angulo_base = (self.index / NUM_ROBOTS) * 2 * math.pi
        radio = 200
        centro_x = 450
        centro_y = 300
        
        x = centro_x + radio * math.cos(angulo_base)
        y = centro_y + radio * math.sin(angulo_base)
        self.teleport(x, y, 0)
        time.sleep(0.5)
        
        # Movimiento circular
        angulo = 0
        step = 0.1  # velocidad angular
        
        while self.ciclos < MAX_CYCLES:
            angulo += step
            self.pos[0] = centro_x + radio * math.cos(angulo_base + angulo)
            self.pos[1] = centro_y + radio * math.sin(angulo_base + angulo)
            self.rot = (angulo_base + angulo) * 180 / math.pi + 90
            
            self.send_state()
            
            # ⚠️ PROBLEMA CRÍTICO: Cada robot duerme independientemente
            # Las pequeñas variaciones en self.delay se acumulan
            time.sleep(self.delay)
            
            # Completar ciclo cada 2π
            if angulo >= 2 * math.pi:
                angulo = 0
                self.ciclos += 1
                # ⚠️ SIMULACIÓN EXTRA de "procesamiento variable"
                # En la realidad, factores como GC, scheduler, etc. causan esto
                time.sleep(random.uniform(0, 0.02))
        
        log(f"  {self.robot_id} terminó (total ciclos: {self.ciclos})")

    def start(self):
        threading.Thread(target=self.movimiento_circular, daemon=True).start()


if __name__ == "__main__":
    log("=" * 60)
    log("EJEMPLO 7: DESINCRONIZACIÓN (Anti-patrón)")
    log("=" * 60)
    log("⚠️  Este ejemplo MUESTRA EL PROBLEMA de threading sin")
    log("   sincronización. Observa cómo los robots que deberían")
    log("   moverse juntos gradualmente se separan.")
    log("")
    log(f"Iniciando {NUM_ROBOTS} robots en movimiento circular...")
    log(f"Ejecutarán {MAX_CYCLES} vueltas completas.")
    log("")
    
    robots = [RobotDesincronizado(f"R{i+1}", i) for i in range(NUM_ROBOTS)]
    
    for r in robots:
        r.start()
    
    # Monitoreo
    inicio = time.time()
    while any(r.ciclos < MAX_CYCLES for r in robots):
        time.sleep(1)
        completados = sum(1 for r in robots if r.ciclos >= MAX_CYCLES)
        if completados > 0:
            log(f"⏱️  {completados}/{NUM_ROBOTS} robots completaron {MAX_CYCLES} ciclos")
    
    tiempo_total = time.time() - inicio
    
    log("")
    log("=" * 60)
    log("RESULTADO: Desincronización observable")
    log("=" * 60)
    log(f"Tiempo total: {tiempo_total:.2f} segundos")
    log("")
    log("🔍 ¿Qué pasó?")
    log("   • Cada robot usó time.sleep() independiente")
    log("   • Pequeñas variaciones de timing se acumularon")
    log("   • Los robots terminaron en momentos diferentes")
    log("   • En la visualización, los círculos se 'desarman'")
    log("")
    log("💡 Solución: Ver ejemplo8_sincronizado.py")
    log("=" * 60)
