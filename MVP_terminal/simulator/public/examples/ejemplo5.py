# -*- coding: utf-8 -*-
# ====================================================
# Programa: 4 Robots que se chocan
# Descripción: Cuatro robots se mueven en un patrón
#              circular, chocando entre sí en el centro
# ====================================================

import socket
import json
import time

# Configuración del simulador
SIM_IP = "127.0.0.1"
SIM_PORT = 10009

def send_state(sock, robot_id, x, y, rot=0, color=None, name=None):
    """Envía el estado de un robot al simulador"""
    packet = {
        "type": "state",
        "src": robot_id,
        "name": name or robot_id,
        "data": {
            "pos": [x, 0, y],
            "rot": rot,
            "color": color or [100, 100, 255]
        }
    }
    msg = json.dumps(packet).encode('utf-8')
    sock.sendto(msg, (SIM_IP, SIM_PORT))

def move_robot_circular(sock, robot_id, center_x, center_y, radius, angle, color, name):
    """Mueve un robot en patrón circular hacia el centro"""
    # Posición actual en círculo
    x = center_x + radius * cos_approx(angle)
    y = center_y + radius * sin_approx(angle)
    
    # Calcular rotación hacia el centro
    rot = (angle + 180) % 360
    
    send_state(sock, robot_id, x, y, rot, color, name)

def cos_approx(degrees):
    """Aproximación simple de coseno"""
    import math
    return math.cos(math.radians(degrees))

def sin_approx(degrees):
    """Aproximación simple de seno"""
    import math
    return math.sin(math.radians(degrees))

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Centro del campo
    center_x, center_y = 450, 300
    
    # Configuración de 4 robots
    robots = [
        {"id": "ROB1", "name": "Norte", "color": [255, 100, 100], "angle": 0},     # Rojo - arriba
        {"id": "ROB2", "name": "Sur", "color": [100, 255, 100], "angle": 180},     # Verde - abajo
        {"id": "ROB3", "name": "Este", "color": [100, 100, 255], "angle": 90},     # Azul - derecha
        {"id": "ROB4", "name": "Oeste", "color": [255, 255, 100], "angle": 270}    # Amarillo - izquierda
    ]
    
    print("Iniciando ejemplo: 4 robots convergiendo al centro")
    print("Los robots se moverán en círculos concéntricos hacia el centro y chocarán")
    
    # Radio inicial
    radius = 250
    
    # Mover robots hacia el centro
    for step in range(100):
        # Reducir radio gradualmente
        current_radius = max(10, radius - step * 2.5)
        
        for robot in robots:
            move_robot_circular(
                sock,
                robot["id"],
                center_x,
                center_y,
                current_radius,
                robot["angle"],
                robot["color"],
                robot["name"]
            )
        
        time.sleep(0.05)  # 50ms entre actualizaciones
    
    print("Ejemplo completado. Los robots deberían estar chocando en el centro.")
    sock.close()
