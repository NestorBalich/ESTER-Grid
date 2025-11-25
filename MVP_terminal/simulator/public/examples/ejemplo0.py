# -*- coding: utf-8 -*-
# Ejemplo 0: Mover en cuadrado (1 robot)
# Secuencia: aparecer en borde del círculo central, avanzar 50px, 
# esperar 1s, girar 90°, repetir 4 veces

import socket, json, time, math

SIM_IP = "127.0.0.1"
SIM_PORT = 10009
TICK_RATE = 0.02  # 20ms
SPEED = 2.5  # píxeles por tick

class Robot:
    def __init__(self, robot_id="E0"):
        self.id = robot_id
        self.pos = [0.0, 0.0]
        self.rot = 0.0  # grados
        self.color = [80, 180, 255]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def teleport(self, x, y, rot=0):
        self.pos = [x, y]
        self.rot = rot
        pkt = {
            "type": "state",
            "src": self.id,
            "name": self.id,
            "cmd": "teleport",
            "cmdData": {"x": x, "y": y, "rot": rot},
            "data": {"pos": [x, 0, y], "rot": rot, "color": self.color},
        }
        self.sock.sendto(json.dumps(pkt).encode(), (SIM_IP, SIM_PORT))

    def send(self):
        pkt = {
            "type": "state",
            "src": self.id,
            "name": self.id,
            "data": {"pos": [self.pos[0], 0, self.pos[1]], "rot": self.rot, "color": self.color},
        }
        self.sock.sendto(json.dumps(pkt).encode(), (SIM_IP, SIM_PORT))

    def avanzar(self, distancia):
        """Avanza 'distancia' píxeles en la dirección actual (rot)"""
        pasos = int(distancia / SPEED)
        rad = math.radians(self.rot)
        dx = SPEED * math.cos(rad)
        dy = SPEED * math.sin(rad)
        
        for _ in range(pasos):
            self.pos[0] += dx
            self.pos[1] += dy
            self.send()
            time.sleep(TICK_RATE)

if __name__ == "__main__":
    r = Robot()
    
    # Centro del canvas 900x600
    centro_x = 450
    centro_y = 300
    
    # Posición inicial: centro de la cancha
    x_inicial = centro_x
    y_inicial = centro_y
    rot_inicial = 0  # Mirando hacia la derecha
    
    print(f"Robot aparece en el centro: ({x_inicial}, {y_inicial})")
    r.teleport(x_inicial, y_inicial, rot_inicial)
    time.sleep(1)
    
    # Hacer cuadrado: 4 lados
    for lado in range(1, 5):
        print(f"Lado {lado}: Avanzando 50px en dirección {r.rot}°")
        r.avanzar(50)
        
        print(f"  Pausa 1 segundo...")
        time.sleep(1)
        
        print(f"  Girando 90° (de {r.rot}° a {(r.rot + 90) % 360}°)")
        r.rot = (r.rot + 90) % 360
        r.send()
        time.sleep(0.3)
    
    print("✓ Cuadrado completado - Robot quedó en la posición final")