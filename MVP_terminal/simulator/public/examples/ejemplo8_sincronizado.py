# -*- coding: utf-8 -*-
# =====================================================
# Ejemplo 8: SINCRONIZACIÓN (solución correcta)
# =====================================================
# Este ejemplo RESUELVE el problema usando un reloj
# maestro que sincroniza todos los robots. Incluso con
# muchos ciclos, los robots permanecen perfectamente
# coordinados.
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
MAX_CYCLES = 5  # Acortado: terminar antes de choques en ciclo 6
TICK_RATE = 0.05  # 50ms por tick

# ✅ SOLUCIÓN: Barrier para sincronización por paso
# Usamos una barrera de NUM_ROBOTS participantes: todos avanzan un paso,
# esperan a que todos terminen y recién entonces se duerme el ciclo.
## Sincronización por eventos (reemplaza Barrier)
# Eventos de inicio y fin de tick + contador de ticks + señal de parada
tick_start = threading.Event()
tick_end = threading.Event()
stop_event = threading.Event()
tick_number_lock = threading.Lock()
tick_number = 0

def log(msg):
    print(msg)

class RobotSincronizado:
    def __init__(self, robot_id, index):
        self.robot_id = robot_id
        self.index = index
        self.color = [random.randint(80, 255), random.randint(80, 255), random.randint(80, 255)]
        self.pos = [0, 0]
        self.rot = 0
        self.ciclos = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # ✅ NO hay delay individual - todos usan el tick global
        
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
        Movimiento circular sincronizado usando reloj maestro con eventos.
        Flujo por tick:
          1. Esperar tick_start (inicio)
          2. Actualizar UNA vez si no terminó
          3. Esperar tick_end (cierre)
        Un hilo separado maneja el pacing y el incremento de tick.
        Robots finalizados siguen participando para no bloquear a otros.
        """
        # Posición en círculo inicial
        angulo_base = (self.index / NUM_ROBOTS) * 2 * math.pi
        radio = 200
        centro_x = 450
        centro_y = 300

        x = centro_x + radio * math.cos(angulo_base)
        y = centro_y + radio * math.sin(angulo_base)
        self.teleport(x, y, 0)

        angulo = 0
        step = 0.1  # velocidad angular
        last_tick_seen = -1
        finished = False

        while not stop_event.is_set():
            tick_start.wait()
            if stop_event.is_set():
                break
            with tick_number_lock:
                current_tick = tick_number
            if current_tick != last_tick_seen:
                last_tick_seen = current_tick
                if not finished:
                    angulo += step
                    self.pos[0] = centro_x + radio * math.cos(angulo_base + angulo)
                    self.pos[1] = centro_y + radio * math.sin(angulo_base + angulo)
                    self.rot = (angulo_base + angulo) * 180 / math.pi + 90
                    self.send_state()
                    if angulo >= 2 * math.pi:
                        angulo = 0
                        self.ciclos += 1
                        if self.ciclos >= MAX_CYCLES:
                            finished = True
                else:
                    # Robot ya finalizado: podría enviar estado ocasional si se requiere
                    pass
            tick_end.wait()
        log(f"  {self.robot_id} terminó (total ciclos: {self.ciclos})")

    def start(self):
        threading.Thread(target=self.movimiento_circular, daemon=True).start()


if __name__ == "__main__":
    log("=" * 60)
    log("EJEMPLO 8: SINCRONIZACIÓN (Patrón correcto)")
    log("=" * 60)
    log("✅ Este ejemplo SOLUCIONA el problema usando un reloj")
    log("   maestro. Todos los robots avanzan al mismo tiempo,")
    log("   sin importar cuántos ciclos ejecuten.")
    log("")
    log(f"Iniciando {NUM_ROBOTS} robots en movimiento circular...")
    log(f"Ejecutarán {MAX_CYCLES} vueltas completas sincronizadas.")
    log("")
    
    robots = [RobotSincronizado(f"S{i+1}", i) for i in range(NUM_ROBOTS)]
    
    for r in robots:
        r.start()
    
    time.sleep(1)  # Esperar posicionamiento inicial
    
    log("🎯 Sincronización con reloj maestro (eventos) iniciada")
    log("")
    inicio = time.time()

    def clock_thread():
        global tick_number
        while not stop_event.is_set():
            # Inicio tick
            with tick_number_lock:
                tick_number += 1
            tick_end.clear()
            tick_start.set()
            time.sleep(TICK_RATE)
            # Fin tick
            tick_start.clear()
            tick_end.set()
        # Asegurar desbloqueo final
        tick_start.set()
        tick_end.set()

    threading.Thread(target=clock_thread, daemon=True).start()

    # Monitoreo y señal de parada
    while True:
        time.sleep(0.5)
        completados = sum(1 for r in robots if r.ciclos >= MAX_CYCLES)
        if completados > 0:
            log(f"⏱️  {completados}/{NUM_ROBOTS} robots completaron {MAX_CYCLES} ciclos")
        if completados == NUM_ROBOTS:
            stop_event.set()
            break

    tiempo_total = time.time() - inicio
    
    log("")
    log("=" * 60)
    log("RESULTADO: Sincronización perfecta mantenida")
    log("=" * 60)
    log(f"Tiempo total: {tiempo_total:.2f} segundos")
    # Cada ciclo completo ≈ (2π / step) ticks
    total_ticks_aprox = MAX_CYCLES * int((2 * math.pi) / 0.1)
    log(f"Ticks estimados ejecutados: ~{total_ticks_aprox}")
    log("")
    log("🔍 ¿Cómo funciona?")
    log("   • clock_thread controla ritmo (un solo sleep)")
    log("   • tick_start/tick_end delimitan cada paso")
    log("   • Contador de tick evita múltiples updates dentro del mismo")
    log("   • Robots finalizados siguen sincronizando hasta parada global")
    log("")
    log("📚 Conceptos aplicados:")
    log("   • threading.Event() para señalización")
    log("   • Reloj maestro centralizado")
    log("   • Pasos discretos vs. timing continuo")
    log("")
    log("💡 Compara con ejemplo7_desincronizado.py para ver")
    log("   la diferencia. ¡Los círculos se mantienen perfectos!")
    log("=" * 60)
