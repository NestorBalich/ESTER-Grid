#!/usr/bin/env python3
"""
Ejemplo 8: Sincronización con efecto LATIDO
===========================================
Patrón correcto usando reloj maestro con eventos.

Cada robot:
- Mantiene su posición angular fija en el círculo
- Se mueve radialmente (hacia/desde el centro)
- Gira sobre su propio eje
- Crea efecto de "latido" colectivo (contracción/expansión)

Sincronización perfecta garantizada por reloj maestro centralizado.
"""

import socket
import json
import time
import threading
import math

# Configuración
NUM_ROBOTS = 20
MAX_CYCLES = 10  # 10 latidos completos (contracción + expansión)
TICK_RATE = 0.05  # 50ms por tick
RADIO_MAX = 250  # Radio máximo (posición expandida)
RADIO_MIN = 150  # Radio mínimo (posición contraída)
RADIO_STEP = 2.0  # Cambio de radio por tick (velocidad del latido)

# Sincronización con eventos
tick_start = threading.Event()
tick_end = threading.Event()
stop_event = threading.Event()
tick_number_lock = threading.Lock()
tick_number = 0

def log(msg):
    """Imprime mensaje con timestamp"""
    t = time.time()
    mins = int(t / 60) % 60
    secs = int(t) % 60
    millis = int((t % 1) * 1000)
    print(f"{mins:02d}:{secs:02d}.{millis:03d}: {msg}", flush=True)


class RobotLatido:
    def __init__(self, robot_id, index):
        self.robot_id = robot_id
        self.index = index
        self.pos = [0.0, 0.0]
        self.rot = 0.0
        self.ciclos = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def teleport(self, x, y, rot):
        self.pos = [x, y]
        self.rot = rot
        self.send_state()
        time.sleep(0.1)

    def send_state(self):
        msg = {
            "type": "robot_state",
            "robot_id": self.robot_id,
            "x": self.pos[0],
            "y": self.pos[1],
            "rotation": self.rot
        }
        try:
            self.sock.sendto(json.dumps(msg).encode(), ("127.0.0.1", 10009))
        except Exception:
            pass

    def movimiento_latido(self):
        """
        Movimiento con latido (contracción/expansión radial).
        Cada robot mantiene su posición angular fija y solo varía el radio.
        """
        # Posición angular fija en el círculo (distribuido uniformemente)
        angulo_posicion = (self.index / NUM_ROBOTS) * 2 * math.pi
        centro_x = 450
        centro_y = 300

        # Teleport a posición inicial (expandida)
        x = centro_x + RADIO_MAX * math.cos(angulo_posicion)
        y = centro_y + RADIO_MAX * math.sin(angulo_posicion)
        self.teleport(450, 400, 0)

        # Estado del latido
        radio_actual = RADIO_MAX  # Empezamos expandidos
        expandiendo = False  # Empezamos contrayendo
        ciclos_completados = 0
        
        angulo_rotacion = 0.0  # Rotación propia del robot
        step_rotacion = 0.05
        
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
                    # Actualizar radio (latido contracción/expansión)
                    if expandiendo:
                        radio_actual += RADIO_STEP
                        if radio_actual >= RADIO_MAX:
                            radio_actual = RADIO_MAX
                            expandiendo = False
                            ciclos_completados += 1
                            if self.index == 0:
                                log(f"💓 Ciclo {ciclos_completados}/{MAX_CYCLES} completado - Máxima expansión alcanzada")
                            
                            if ciclos_completados >= MAX_CYCLES:
                                finished = True
                                self.ciclos = ciclos_completados
                    else:
                        # Contrayendo
                        radio_actual -= RADIO_STEP
                        if radio_actual <= RADIO_MIN:
                            radio_actual = RADIO_MIN
                            expandiendo = True
                            if self.index == 0:
                                log(f"💓 Mínima contracción alcanzada - Iniciando expansión (ciclo {ciclos_completados + 1}/{MAX_CYCLES})")
                    
                    # Calcular posición (ángulo fijo, radio variable)
                    self.pos[0] = centro_x + radio_actual * math.cos(angulo_posicion)
                    self.pos[1] = centro_y + radio_actual * math.sin(angulo_posicion)
                    
                    # Rotación propia del robot
                    angulo_rotacion += step_rotacion
                    self.rot = angulo_rotacion * 180 / math.pi
                    
                    # Debug cada 100 ticks (solo robot 0)
                    if self.index == 0 and current_tick % 100 == 0:
                        dist_centro = math.sqrt((self.pos[0] - centro_x)**2 + (self.pos[1] - centro_y)**2)
                        fase = "EXPANDIR" if expandiendo else "CONTRAER"
                        log(f"🔍 R{self.robot_id} Tick{current_tick} | fase={fase} radio={radio_actual:.0f} dist={dist_centro:.0f} ciclos={ciclos_completados}")
                    
                    self.send_state()
            tick_end.wait()
        log(f"  {self.robot_id} terminó (total ciclos: {self.ciclos})")

    def start(self):
        threading.Thread(target=self.movimiento_latido, daemon=True).start()


if __name__ == "__main__":
    log("=" * 60)
    log("EJEMPLO 8: LATIDO SINCRONIZADO (Patrón correcto)")
    log("=" * 60)
    log("✅ Movimiento radial puro: contracción y expansión")
    log("   Todos los robots late en perfecta sincronía.")
    log("")
    log(f"Iniciando {NUM_ROBOTS} robots en formación circular...")
    log(f"Ejecutarán {MAX_CYCLES} latidos completos sincronizados.")
    log("")
    
    robots = [RobotLatido(f"L{i+1}", i) for i in range(NUM_ROBOTS)]
    
    for r in robots:
        r.start()
    
    time.sleep(1)  # Esperar posicionamiento inicial
    
    log("🎯 Sincronización con reloj maestro (eventos) iniciada")
    log("")
    inicio = time.time()

    # Hilo reloj maestro
    def clock_thread():
        global tick_number
        while True:
            with tick_number_lock:
                tick_number += 1
            tick_start.set()
            time.sleep(TICK_RATE)
            tick_start.clear()
            tick_end.set()
            time.sleep(0.001)
            tick_end.clear()

    threading.Thread(target=clock_thread, daemon=True).start()

    # Hilo monitor: detecta cuando todos terminaron
    def monitor_thread():
        while True:
            if all(r.ciclos >= MAX_CYCLES for r in robots):
                stop_event.set()
                break
            time.sleep(0.5)

    threading.Thread(target=monitor_thread, daemon=True).start()

    # Esperar a que stop_event se active
    stop_event.wait()
    fin = time.time()

    log(f"⏱️  {len([r for r in robots if r.ciclos >= MAX_CYCLES])}/{NUM_ROBOTS} robots completaron {MAX_CYCLES} latidos")
    log("")
    log("=" * 60)
    log("RESULTADO: Sincronización perfecta mantenida")
    log("=" * 60)
    log(f"Tiempo total: {fin - inicio:.2f} segundos")
    with tick_number_lock:
        log(f"Ticks totales ejecutados: {tick_number}")
    log("")
    log("🔍 ¿Cómo funciona?")
    log("   • clock_thread controla ritmo (un solo sleep)")
    log("   • tick_start/tick_end delimitan cada paso")
    log("   • Contador de tick evita múltiples updates")
    log("   • Radio aumenta/disminuye cada tick sincronizadamente")
    log("")
    log("📚 Conceptos aplicados:")
    log("   • threading.Event() para señalización")
    log("   • Reloj maestro centralizado")
    log("   • Movimiento radial (latido)")
    log("")
    log("💡 Compara con ejemplo7_desincronizado.py para ver")
    log("   la diferencia. ¡El latido es perfectamente sincronizado!")
    log("=" * 60)
