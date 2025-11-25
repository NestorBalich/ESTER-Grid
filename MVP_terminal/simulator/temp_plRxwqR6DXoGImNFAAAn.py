import sys
sys.stdout.reconfigure(encoding='utf-8')
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
MAX_CYCLES = 10  # 10 vueltas completas
TICK_RATE = 0.05  # 50ms por tick
RADIO_MAX = 250  # Radio máximo del círculo (aumentado para empezar más grande)
RADIO_MIN = 150   # Radio mínimo (centro) - NO BAJAR de 150 para evitar choques
ANGLE_CHANGE_DIRECTION = math.pi * 0.4  # Ángulo donde cambia (40% del ciclo = cambia antes de chocar)
RADIO_STEP = 2.0  # Cuánto se acerca/aleja por tick

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
        El radio se contrae hacia el centro y luego se expande en cada ciclo.
        Flujo por tick:
          1. Esperar tick_start (inicio)
          2. Actualizar UNA vez si no terminó
          3. Esperar tick_end (cierre)
        Un hilo separado maneja el pacing y el incremento de tick.
        Robots finalizados siguen participando para no bloquear a otros.
        """
        # Posición en círculo inicial
        angulo_base = (self.index / NUM_ROBOTS) * 2 * math.pi
        centro_x = 450
        centro_y = 300

        x = centro_x + RADIO_MAX * math.cos(angulo_base)
        y = centro_y + RADIO_MAX * math.sin(angulo_base)
        self.teleport(x, y, 0)

        angulo = 0
        step = 0.1  # velocidad angular
        last_tick_seen = -1
        finished = False
        ultimo_ciclo_reportado = -1

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
                    
                    # Verificar si completamos todos los ciclos ANTES de calcular
                    if angulo >= 2 * math.pi * MAX_CYCLES:
                        finished = True
                        continue
                    
                    # Determinar ciclo actual (0 a MAX_CYCLES-1)
                    ciclo_actual = int(angulo / (2 * math.pi))
                    angulo_en_ciclo = angulo % (2 * math.pi)
                    
                    # Reportar cambio de ciclo (solo robot 0 para no saturar logs)
                    if self.index == 0 and ciclo_actual != ultimo_ciclo_reportado:
                        fase = "CONTRAER" if ciclo_actual < MAX_CYCLES / 2 else "EXPANDIR"
                        # Calcular radio objetivo para este ciclo
                        if ciclo_actual < MAX_CYCLES / 2:
                            # Contracción: ciclo 1→250, ciclo 2→230, ciclo 3→210, ciclo 4→190, ciclo 5→170
                            progress_contraccion = ciclo_actual / (MAX_CYCLES / 2)
                            radio_obj = RADIO_MAX - (RADIO_MAX - RADIO_MIN) * progress_contraccion
                        else:
                            # Expansión: ciclo 6→170, ciclo 7→190, ciclo 8→210, ciclo 9→230, ciclo 10→250
                            # Ciclo 6 (índice 5) es el primero post-contracción, mantiene radio mínimo
                            # Luego expande gradualmente
                            ciclos_desde_mitad = ciclo_actual - MAX_CYCLES / 2  # 0,1,2,3,4
                            progress_expansion = ciclos_desde_mitad / (MAX_CYCLES / 2)  # 0, 0.2, 0.4, 0.6, 0.8
                            radio_obj = RADIO_MIN + (RADIO_MAX - RADIO_MIN) * progress_expansion
                        log(f"📍 Ciclo {ciclo_actual + 1}/{MAX_CYCLES} - Fase: {fase} - Radio objetivo: {radio_obj:.0f}")
                        ultimo_ciclo_reportado = ciclo_actual
                    
                    # Estrategia global: primera mitad de ciclos → contraer, segunda mitad → expandir
                    if ciclo_actual < MAX_CYCLES / 2:
                        # Primera mitad (ciclos 0-4): contraer progresivamente
                        progress_contraccion = ciclo_actual / (MAX_CYCLES / 2)
                        radio_objetivo = RADIO_MAX - (RADIO_MAX - RADIO_MIN) * progress_contraccion
                        
                        # Dentro del ciclo: siempre empezar desde RADIO_MAX
                        if angulo_en_ciclo < ANGLE_CHANGE_DIRECTION:
                            progress = angulo_en_ciclo / ANGLE_CHANGE_DIRECTION
                            radio = RADIO_MAX - (RADIO_MAX - radio_objetivo) * progress
                        else:
                            radio = radio_objetivo
                    else:
                        # Segunda mitad (ciclos 5-9): expandir progresivamente desde MIN hacia MAX
                        # Cambiar completamente: empezar desde RADIO_MIN y crecer hacia RADIO_MAX
                        progress_expansion = (ciclo_actual - MAX_CYCLES / 2 + 1) / (MAX_CYCLES / 2)
                        radio_objetivo = RADIO_MIN + (RADIO_MAX - RADIO_MIN) * progress_expansion
                        
                        # Dentro del ciclo: SIEMPRE partir desde RADIO_MIN y expandir
                        if angulo_en_ciclo < ANGLE_CHANGE_DIRECTION:
                            progress = angulo_en_ciclo / ANGLE_CHANGE_DIRECTION
                            radio = RADIO_MIN + (radio_objetivo - RADIO_MIN) * progress
                        else:
                            radio = radio_objetivo
                    
                    self.pos[0] = centro_x + radio * math.cos(angulo_base + angulo)
                    self.pos[1] = centro_y + radio * math.sin(angulo_base + angulo)
                    self.rot = (angulo_base + angulo) * 180 / math.pi + 90
                    
                    # Debug: log posición cada 100 ticks (solo robot 0)
                    if self.index == 0 and current_tick % 100 == 0:
                        dist_centro = math.sqrt((self.pos[0] - centro_x)**2 + (self.pos[1] - centro_y)**2)
                        log(f"🔍 R{self.robot_id} Tick{current_tick} Ciclo{ciclo_actual+1} | pos=({self.pos[0]:.0f},{self.pos[1]:.0f}) radio={radio:.0f} dist_centro={dist_centro:.0f}")
                    
                    self.send_state()
                    if angulo >= 2 * math.pi * MAX_CYCLES:
                        finished = True
                        self.ciclos = MAX_CYCLES
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