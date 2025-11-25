# =====================================================
# EGUP v3 - Máquina de estados con control de tiempo no bloqueante
# =====================================================

import socket
import json
import time
import math

ROBOT_ID = "ROB1"
UDP_PORT = 9999
DISPATCHER_ADDR = ("127.0.0.1", UDP_PORT)

# Posición inicial / centro
INIT_POS = [450, 200]

# Estado del robot
robot_state = {
    "pos": INIT_POS.copy(),
    "rot": 0,
    "color": (255, 100, 50)
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Máquina de estados
STATE = 0
TARGET_POS = None
CENTER_POS = INIT_POS.copy()  # punto central al que debe mirar en Estado 2 y 3

# Para el movimiento circular en Estado 3
CIRCLE_RADIUS = 50
circle_angle = 0  # ángulo actual alrededor del círculo

# Control de tiempo por estado
STATE_START_TIME = time.time()

def teletransportar(x=None, y=None, rot=None):
    if x is not None:
        robot_state["pos"][0] = x
    if y is not None:
        robot_state["pos"][1] = y
    if rot is not None:
        robot_state["rot"] = rot
    print(f"[{ROBOT_ID}] Teletransportado a x={robot_state['pos'][0]}, y={robot_state['pos'][1]}, rot={robot_state['rot']}°")

def send_state(cmd=None, cmd_data=None):
    packet = {
        "src": ROBOT_ID,
        "dst": "dispatcher",
        "type": "state",
        "data": robot_state,
        "ts": int(time.time() * 1000)
    }
    if cmd:
        packet["cmd"] = cmd
        packet["cmdData"] = cmd_data
    sock.sendto(json.dumps(packet).encode(), DISPATCHER_ADDR)

def rotar_hacia(target):
    dx = target[0] - robot_state["pos"][0]
    dy = target[1] - robot_state["pos"][1]
    angle = math.degrees(math.atan2(dy, dx)) % 360
    robot_state["rot"] = angle
    print(f"[{ROBOT_ID}] Rotando hacia {angle:.1f}°")

def girar_alrededor(centro, actual, angulo_grados):
    cx, cy = centro
    x, y = actual
    radio = math.hypot(x - cx, y - cy)
    ang_actual = math.atan2(y - cy, x - cx)
    ang_nuevo = ang_actual + math.radians(angulo_grados)
    nx = cx + radio * math.cos(ang_nuevo)
    ny = cy + radio * math.sin(ang_nuevo)
    return [nx, ny]

STATE_DURATIONS = {
    0: 1,   # tiempo en segundos para Estado 0
    1: 2,   # tiempo en Estado 1
    2: 1,   # tiempo en Estado 2 (solo rotar)
    3: 1 # Estado 3 indefinido, gira continuamente
}

RADIO_CIRCLE = 200
ANGULO_POR_ITERACION = 10
while True:
    current_time = time.time()
    elapsed = current_time - STATE_START_TIME

    if STATE == 0:
        # Estado 0: teleport inicial
        teletransportar(INIT_POS[0], INIT_POS[1], 0)
        send_state("teleport", {"x": INIT_POS[0], "y": INIT_POS[1], "rot": 0})
        TARGET_POS = [INIT_POS[0] + 100, INIT_POS[1]]  # punto para moverse en X
        STATE_START_TIME = time.time()
        STATE = 1

    elif STATE == 1:
        # Estado 1: mover RADIO_CIRCLE unidades en X
        robot_state["pos"][0] += RADIO_CIRCLE
        send_state("move", {"x": robot_state["pos"][0], "y": robot_state["pos"][1]})
        
        # Guardar la posición final en TARGET_POS para usar en Estado 3
        TARGET_POS = robot_state["pos"].copy()

        if elapsed >= STATE_DURATIONS[1]:
            STATE = 2
            STATE_START_TIME = time.time()

    elif STATE == 2:
        # Estado 2: rotar mirando al centro desde la posición actual
        rotar_hacia(CENTER_POS)
        send_state("rotate_toward_center", {"rot": robot_state["rot"]})

        if elapsed >= STATE_DURATIONS[2]:
            STATE = 3
            STATE_START_TIME = time.time()
            robot_state["pos"] = TARGET_POS.copy()

    elif STATE == 3:


        if elapsed >= STATE_DURATIONS[3]:
            STATE = 3
            STATE_START_TIME = time.time()

    # Pequeña pausa para no saturar el CPU
    time.sleep(0.05)
