# ========================================================
# ESTER-Grid 2D Map Viewer Mejorado
# Movimiento suave + Reconexión + Fade Out visual + Color + Estado GPS/Colisión
# Objetos movibles/inamovibles y detección de colisión realista
# GPS solo se envía si hay cambio de posición
# Bumper solo envía cuando hay colisión
# Nombre del robot siempre visible
# ========================================================

import pygame
import socket
import json
import time
import threading
import random

# ----------------------------
# CONFIG
# ----------------------------
UDP_PORT = 9999
WINDOW_W, WINDOW_H = 900, 600
ROBOT_SIZE = 10
ROBOT_SPEED = 2.0
TIMEOUT_SEC = 2
FADE_SPEED = 0.05
STATE_SEND_INTERVAL = 0.05
OBJ_COUNT = 50
OBJ_WIDTH = 25
OBJ_HEIGHT = 15

# ----------------------------
# UDP Socket
# ----------------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))
sock.setblocking(False)

robots = {}
objects = []

pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("ESTER-Grid MAPA 2D Mejorado")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 18)

# ----------------------------
# Helpers
# ----------------------------
def clamp_pos(x, y):
    x = max(0, min(WINDOW_W, x))
    y = max(0, min(WINDOW_H, y))
    return x, y

def robot_color(rid):
    seed = sum(ord(c) for c in rid)
    return ((seed * 50) % 255, (seed * 80) % 255, (seed * 110) % 255)

# ----------------------------
# Crear objetos aleatorios
# ----------------------------
def create_objects():
    for i in range(OBJ_COUNT):
        obj_type = random.choice(["movible", "inamovible"])
        obj_name = f"{obj_type[:3]}_{i}"
        x = random.randint(50, WINDOW_W-50)
        y = random.randint(50, WINDOW_H-50)
        color = (255, 0, 0) if obj_type == "inamovible" else (random.randint(50,255), random.randint(50,255), random.randint(50,255))
        objects.append({
            "x": x, "y": y, "type": obj_type, "name": obj_name,
            "color": color, "width": OBJ_WIDTH, "height": OBJ_HEIGHT
        })

create_objects()

# ----------------------------
# UDP Receiver Thread
# ----------------------------
def udp_receiver():
    global robots
    while True:
        try:
            msg, addr = sock.recvfrom(4096)
            packet = json.loads(msg.decode())
            if packet.get("type") != "state":
                continue

            rid = packet["src"]
            px, py = packet["data"]["pos"][0], packet["data"]["pos"][1]
            px, py = clamp_pos(px, py)
            rot = packet["data"].get("rot", 0)
            color = packet["data"].get("color", robot_color(rid))

            if rid not in robots:
                robots[rid] = {
                    "x": px, "y": py, "tx": px, "ty": py,
                    "rot": rot, "last_seen": time.time(), "alpha": 255,
                    "color": color, "collision": {"collision": False}
                }
            else:
                rb = robots[rid]
                rb["tx"] = px
                rb["ty"] = py
                rb["rot"] = rot
                rb["last_seen"] = time.time()
                rb["alpha"] = 255
                rb["color"] = color

        except BlockingIOError:
            time.sleep(0.01)
            continue
        except Exception as e:
            print("Error UDP:", e)

threading.Thread(target=udp_receiver, daemon=True).start()

# ----------------------------
# Movimiento y colisión
# ----------------------------
def apply_movement(rb):
    dx = rb["tx"] - rb["x"]
    dy = rb["ty"] - rb["y"]
    dist = (dx*dx + dy*dy)**0.5
    if dist == 0:
        return False, None  # No movimiento, no enviar GPS

    move_dx = dx / dist * min(dist, ROBOT_SPEED)
    move_dy = dy / dist * min(dist, ROBOT_SPEED)
    collision_info = {"collision": False}

    for obj in objects:
        dist_x = abs(rb["x"] + move_dx - obj["x"])
        dist_y = abs(rb["y"] + move_dy - obj["y"])
        overlap_x = (ROBOT_SIZE + obj["width"]/2) - dist_x
        overlap_y = (ROBOT_SIZE + obj["height"]/2) - dist_y

        if overlap_x > 0 and overlap_y > 0:
            collision_info = {"collision": True, "type": obj["type"], "name": obj["name"]}
            if obj["type"] == "movible":
                obj["x"] += move_dx
                obj["y"] += move_dy
            else:  # inamovible bloquea
                move_dx, move_dy = 0, 0

    rb["x"] += move_dx
    rb["y"] += move_dy
    return True, collision_info if collision_info["collision"] else None

# ----------------------------
# Enviar estado GPS + colisión
# ----------------------------
def send_state_info():
    while True:
        now = time.time()
        for rid in list(robots.keys()):
            rb = robots[rid]
            moved, collision = apply_movement(rb)
            if moved or collision:
                data = {"gps": [rb["x"], rb["y"]]}
                if collision:
                    data["collision"] = collision
                state_packet = {
                    "src": "mapa",
                    "dst": rid,
                    "type": "state_info",
                    "data": data,
                    "ts": int(now*1000)
                }
                sock.sendto(json.dumps(state_packet).encode(), ("127.0.0.1", UDP_PORT))
        time.sleep(STATE_SEND_INTERVAL)

threading.Thread(target=send_state_info, daemon=True).start()

# ----------------------------
# Main Loop
# ----------------------------
running = True
while running:
    screen.fill((30,30,30))
    to_remove = []

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    for rid in list(robots.keys()):
        rb = robots[rid]
        if time.time() - rb["last_seen"] > TIMEOUT_SEC:
            rb["alpha"] -= int(FADE_SPEED*255)
            if rb["alpha"] <= 0:
                to_remove.append(rid)
                continue

        # dibujar robot
        s = pygame.Surface((ROBOT_SIZE*2, ROBOT_SIZE*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*rb["color"], rb["alpha"]), (ROBOT_SIZE, ROBOT_SIZE), ROBOT_SIZE)
        screen.blit(s, (int(rb["x"]-ROBOT_SIZE), int(rb["y"]-ROBOT_SIZE)))

        # orientación
        dx = ROBOT_SIZE*1.5
        nx = rb["x"] + dx * pygame.math.Vector2(1,0).rotate(-rb["rot"]).x
        ny = rb["y"] + dx * pygame.math.Vector2(1,0).rotate(-rb["rot"]).y
        pygame.draw.line(screen, (255,255,0), (rb["x"], rb["y"]), (nx, ny), 2)

        # nombre siempre visible, colisión solo si ocurre
        col_text = ""
        if rb["collision"].get("collision"):
            col_text = f"COL {rb['collision'].get('name','')}"
        label = font.render(f"{rid} {col_text}", True, (255,255,255))
        screen.blit(label, (rb["x"] + 12, rb["y"] - 12))

    # dibujar objetos
    for obj in objects:
        pygame.draw.rect(screen, obj["color"],
                         (obj["x"]-obj["width"]/2, obj["y"]-obj["height"]/2, obj["width"], obj["height"]))

    for rid in to_remove:
        del robots[rid]

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
