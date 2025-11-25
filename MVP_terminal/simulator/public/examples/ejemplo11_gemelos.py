# -*- coding: utf-8 -*-
# =====================================================
# Ejemplo 11: Modo Gemelo Digital (Digital Twin)
# =====================================================
# Demuestra el modo gemelo donde un robot físico y su
# gemelo digital están sincronizados:
# - Ambos reciben los mismos comandos
# - Ambos comparten información de sensores
# - Escalable a múltiples pares gemelos (ej: 30 físicos + 30 gemelos)
#
# En este ejemplo:
# - 4 robots físicos (PHYS_A, PHYS_B, PHYS_C, PHYS_D)
# - 3 gemelos digitales (TWIN_A, TWIN_B, TWIN_C) — el cuarto no tiene gemelo
# - Cada par se mueve sincronizado (A,B,C) pero D opera sin gemelo para ver contraste
# =====================================================

import socket
import json
import time
import threading
import math

SIM_IP = "127.0.0.1"
SIM_PORT = 10009

DISP_IP = "127.0.0.1"
DISP_MSG_PORT = 10011

WINDOW_W = 900
WINDOW_H = 600
CENTER_X = WINDOW_W // 2
CENTER_Y = WINDOW_H // 2

class Robot:
    def __init__(self, robot_id, start_pos, start_rot=0, color=None, is_twin=False):
        self.robot_id = robot_id
        self.pos = [start_pos[0], start_pos[1]]
        self.rot = start_rot
        self.color = color or [200, 200, 200]
        self.is_twin = is_twin
        self.twin_id = None
        
        # Sockets
        self.sock_state = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_msg = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # El gemelo necesita escuchar estados replicados
        if is_twin:
            self.sock_msg.bind(('0.0.0.0', 0))  # bind a puerto aleatorio
            self.listen_port = self.sock_msg.getsockname()[1]
            print(f"[{robot_id}] Gemelo escuchando en puerto {self.listen_port}")
        
        self.sock_msg.settimeout(0.05)
        
        # Offset visual para gemelos (para verlos lado a lado)
        self.visual_offset = [30, 0] if is_twin else [0, 0]

    def send_state(self):
        # Aplicar offset visual solo para gemelos
        x = self.pos[0] + self.visual_offset[0]
        y = self.pos[1] + self.visual_offset[1]
        
        packet = {
            "type": "state",
            "src": self.robot_id,
            "name": self.robot_id,
            "data": {
                "pos": [x, 0, y],
                "rot": self.rot,
                "color": self.color
            }
        }
        # Enviar al simulador directamente
        self.sock_state.sendto(json.dumps(packet).encode('utf-8'), (SIM_IP, SIM_PORT))
        # Y también al dispatcher para replicación a gemelo
        self.sock_msg.sendto(json.dumps(packet).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def teleport(self, x, y, rot):
        self.pos = [x, y]
        self.rot = rot
        
        # Aplicar offset visual
        vx = x + self.visual_offset[0]
        vy = y + self.visual_offset[1]
        
        packet = {
            "type": "state",
            "src": self.robot_id,
            "name": self.robot_id,
            "cmd": "teleport",
            "cmdData": {"x": vx, "y": vy, "rot": rot},
            "data": {
                "pos": [vx, 0, vy],
                "rot": rot,
                "color": self.color
            }
        }
        # Enviar al simulador directamente
        self.sock_state.sendto(json.dumps(packet).encode('utf-8'), (SIM_IP, SIM_PORT))
        # Y también al dispatcher para replicación a gemelo
        self.sock_msg.sendto(json.dumps(packet).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def register(self):
        pkt = {"type": "register", "src": self.robot_id}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def register_twin(self, twin_id):
        self.twin_id = twin_id
        pkt = {"type": "twin_register", "src": self.robot_id, "twin": twin_id}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def unregister_twin(self):
        if self.twin_id:
            pkt = {"type": "twin_unregister", "src": self.robot_id}
            self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def send_msg(self, to, data):
        mid = f"{self.robot_id}_{int(time.time()*1000)}"
        pkt = {"type": "msg", "src": self.robot_id, "to": to, "mid": mid, "data": data}
        self.sock_msg.sendto(json.dumps(pkt).encode('utf-8'), (DISP_IP, DISP_MSG_PORT))

    def recv_any(self):
        try:
            data, _ = self.sock_msg.recvfrom(4096)
            pkt = json.loads(data.decode('utf-8'))
            return pkt
        except socket.timeout:
            return None

    def move_to(self, x, y, step_px=3.0):
        dx = x - self.pos[0]
        dy = y - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist < 0.01:
            return True
        k = min(step_px, dist) / (dist if dist > 0 else 1)
        self.pos[0] += dx * k
        self.pos[1] += dy * k
        self.rot = (math.degrees(math.atan2(dy, dx)) + 360) % 360
        self.send_state()
        return False


# ===================================
# Coordinar pares gemelos
# ===================================

def robot_pair_thread(phys_id, twin_id, path_points, color_phys, color_twin):
    """
    Ejecuta un robot físico y su gemelo.
    
    IMPORTANTE:
    - El robot físico ejecuta su lógica de movimiento completa
    - El gemelo NO tiene lógica de movimiento propia
    - El gemelo SOLO actualiza su posición basándose en lo que recibe del dispatcher
    """
    # Crear robots
    start_x, start_y = path_points[0]
    phys = Robot(phys_id, (start_x, start_y), 0, color_phys, is_twin=False)
    twin = Robot(twin_id, (start_x, start_y), 0, color_twin, is_twin=True)

    # Registrar ambos en dispatcher
    phys.register()
    twin.register()
    time.sleep(0.1)

    # Registrar par gemelo
    phys.register_twin(twin_id)
    time.sleep(0.1)

    # Teleportar ambos a posición inicial
    phys.teleport(start_x, start_y, 0)
    twin.teleport(start_x, start_y, 0)
    
    print(f"[{phys_id}] Robot físico iniciando movimiento")
    print(f"[{twin_id}] Gemelo en modo PASIVO - solo replica estados")

    # Thread para el gemelo: SOLO ESCUCHA, NO SE MUEVE POR SÍ MISMO
    def twin_listener():
        """
        El gemelo NO calcula movimientos.
        Solo espera estados replicados del dispatcher.
        """
        while True:
            pkt = twin.recv_any()
            if pkt and pkt.get('type') == 'state' and pkt.get('mirrored_from') == phys_id:
                # Recibió estado replicado del físico por el dispatcher
                data = pkt.get('data', {})
                if data.get('pos'):
                    pos = data['pos']
                    # Actualizar posición sin offset (el offset ya viene en los datos)
                    twin.pos[0] = pos[0] - twin.visual_offset[0] if len(pos) > 0 else twin.pos[0]
                    twin.pos[1] = pos[2] - twin.visual_offset[1] if len(pos) > 2 else twin.pos[1]
                if data.get('rot') is not None:
                    twin.rot = data['rot']
                # Enviar estado actualizado al simulador
                twin.send_state()
                print(f"[{twin_id}] Replicado: pos=({twin.pos[0]:.1f}, {twin.pos[1]:.1f}), rot={twin.rot:.1f}")
            time.sleep(0.01)
    
    listener_thread = threading.Thread(target=twin_listener, daemon=True)
    listener_thread.start()

    # SOLO EL ROBOT FÍSICO EJECUTA LA LÓGICA DE MOVIMIENTO
    # El gemelo NO tiene acceso a path_points ni ejecuta move_to()
    for idx, (target_x, target_y) in enumerate(path_points[1:], 1):
        print(f"[{phys_id}] Moviéndose al punto {idx}/{len(path_points)-1}: ({target_x}, {target_y})")
        while not phys.move_to(target_x, target_y):
            time.sleep(0.02)
        time.sleep(0.3)

    print(f"[{phys_id}] ✓ Movimiento completado")
    print(f"[{twin_id}] ✓ Replicación completada")

    # Desregistrar gemelos
    phys.unregister_twin()
    time.sleep(0.5)  # Dar tiempo para que el gemelo procese últimos paquetes


# ===================================
# Patrones de movimiento para cada par
# ===================================

def get_triangle_path(center_x, center_y, size=80):
    return [
        (center_x, center_y - size),
        (center_x + size, center_y + size//2),
        (center_x - size, center_y + size//2),
        (center_x, center_y - size)
    ]

def get_square_path(center_x, center_y, size=70):
    return [
        (center_x - size, center_y - size),
        (center_x + size, center_y - size),
        (center_x + size, center_y + size),
        (center_x - size, center_y + size),
        (center_x - size, center_y - size)
    ]

def get_circle_path(center_x, center_y, radius=60, points=12):
    path = []
    for i in range(points + 1):
        angle = (i / points) * 2 * math.pi
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        path.append((x, y))
    return path


if __name__ == "__main__":
    print("=" * 70)
    print("Ejemplo 11: Modo Gemelo Digital (Digital Twin)")
    print("=" * 70)
    print("4 robots físicos (A,B,C,D) + 3 gemelos digitales (A,B,C). D sin gemelo")
    print("Los gemelos replican automáticamente los comandos del físico")
    print("=" * 70)

    # Definir pares y sus patrones
    pairs = [
        {
            "phys_id": "PHYS_A",
            "twin_id": "TWIN_A",
            "path": get_triangle_path(CENTER_X - 200, CENTER_Y, 60),
            "color_phys": [255, 100, 100],  # rojo
            "color_twin": [255, 200, 200]   # rojo claro
        },
        {
            "phys_id": "PHYS_B",
            "twin_id": "TWIN_B",
            "path": get_square_path(CENTER_X, CENTER_Y, 60),
            "color_phys": [100, 255, 100],  # verde
            "color_twin": [200, 255, 200]   # verde claro
        },
        {
            "phys_id": "PHYS_C",
            "twin_id": "TWIN_C",
            "path": get_circle_path(CENTER_X + 200, CENTER_Y, 50),
            "color_phys": [100, 100, 255],  # azul
            "color_twin": [200, 200, 255]   # azul claro
        }
    ]

    # Robot físico sin gemelo (PHYS_D)
    solo_path = get_square_path(CENTER_X + 320, CENTER_Y - 40, 45)

    def phys_only_thread(phys_id, path, color_phys):
        start_x, start_y = path[0]
        phys = Robot(phys_id, (start_x, start_y), 0, color_phys, is_twin=False)
        phys.register()
        time.sleep(0.1)
        phys.teleport(start_x, start_y, 0)
        print(f"[{phys_id}] Robot físico SIN gemelo iniciando movimiento")
        for idx, (tx, ty) in enumerate(path[1:], 1):
            print(f"[{phys_id}] Moviéndose al punto {idx}/{len(path)-1}: ({tx:.1f}, {ty:.1f})")
            while not phys.move_to(tx, ty):
                time.sleep(0.02)
            time.sleep(0.25)
        print(f"[{phys_id}] ✓ Movimiento completado (sin gemelo)\n")

    # Lanzar threads para cada par
    threads = []
    for pair in pairs:
        t = threading.Thread(
            target=robot_pair_thread,
            args=(pair["phys_id"], pair["twin_id"], pair["path"], 
                  pair["color_phys"], pair["color_twin"]),
            daemon=True
        )
        threads.append(t)
        t.start()
        time.sleep(0.2)  # pequeño delay entre inicios

    # Lanzar thread para robot sin gemelo
    t_d = threading.Thread(
        target=phys_only_thread,
        args=("PHYS_D", solo_path, [255, 230, 90]),  # amarillo
        daemon=True
    )
    threads.append(t_d)
    t_d.start()

    # Esperar a que todos terminen
    for t in threads:
        t.join()

    time.sleep(1)
    print("=" * 70)
    print("✔️ Ejemplo 11 finalizado")
    print("Pares gemelos completaron trayectorias y PHYS_D finalizó sin gemelo")
    print("=" * 70)
