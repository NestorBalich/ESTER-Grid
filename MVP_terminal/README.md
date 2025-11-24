ESTER-Grid – MVP de Comunicación Robot-UDP
Modelo híbrido Node.js + Python para red de robots simulados

Este repositorio contiene el prototipo mínimo viable (MVP) del sistema de comunicación distribuida para robots del futuro simulador ESTER-Grid.
El objetivo es validar la asignación dinámica de puertos, mensajería UDP, enrutamiento entre robots, sincronización por timestamp y estructura de paquetes JSON estándar, antes de integrar los robots simulados en Godot y los robots físicos ESP32.

🚀 Objetivos del MVP

Crear una base de comunicación universal para robots (simulados o reales).

Validar el modelo Robot-PUSH, donde cada robot solo necesita saber:

Su robot_id,

Su puerto UDP asignado,

La dirección del dispatcher.

Implementar:

dispatcher (Node.js): asignador de puertos + router opcional

robot_listener (Python): escucha respuestas recibidas

robot_mesh (Python): comunicación robot-robot (si se necesita)

Definir un formato JSON estándar para todos los paquetes.

Permitir extender a robots físicos ESP32 sin cambiar la arquitectura.

Preparar el sistema para que Godot pueda integrarse luego como frontend visual.

🧱 Arquitectura del MVP
                            +------------------------+
                            |   Dispatcher (Node)    |
                            |  - Registro robots     |
                            |  - Asignación de UDP   |
                            |  - Tabla de rutas      |
                            +----------+-------------+
                                       |
                 ---------------------------------------------------
                 |                         |                        |
      +----------v-----+        +----------v-----+        +---------v-------+
      |  Robot A (Py)  |        |  Robot B (Py)  |        | Robot C (Py)    |
      |  - send()      |        |  - send()      |        | - send()        |
      |  - listener()  |        |  - listener()  |        | - listener()    |
      |  - mesh UDP    |        |  - mesh UDP    |        | - mesh UDP      |
      +----------------+        +----------------+        +-----------------+


Todos los robots usan:

UDP directo entre ellos

UDP hacia/desde dispatcher

Paquetes JSON estándar

timestamp obligatorio

📦 Componentes del repositorio
1. dispatcher/ (Node.js)

Servidor que:

Crea una tabla de robots

Asigna puertos UDP libres

Resuelve a quién corresponde cada mensaje

Permite consultar información sobre otros robots

Archivos:

dispatcher.js

robots.json (se genera solo)

config.json

2. robot_listener.py (Python)

Escucha por UDP el puerto asignado al robot

Procesa paquetes entrantes

Emite eventos al robot (futuro: integración Godot)

3. robot_mesh.py (Python)

Envía mensajes UDP directos a cualquier robot

Recibe info del dispatcher sobre qué puerto usar

Implementa el patrón:
robot → robot
robot → dispatcher
robot → muchos robots (broadcast)

🔧 Instalación
Node.js (dispatcher)
cd dispatcher
npm install
node dispatcher.js

Python (robots)

Requisitos:

pip install asyncio aiohttp


Ejecutar robot A:

python robot_listener.py --id ROB4351

📡 Formato estándar de paquete JSON

Este es el único formato válido para todos los mensajes:

{
  "from": "ROB4351",
  "to": "ROB9999",
  "type": "command",
  "command": "move",
  "value": "forward",
  "timestamp": 1761674194575
}

Campos obligatorios:
Campo	Descripción
from	Emisor (robot_id)
to	Destino (robot_id o "broadcast")
type	tipo de mensaje ("command", "sensor", "info", "state", "ping")
command	Acción específica
value	Argumento del comando
timestamp	Marca de tiempo en milisegundos
🌐 Flujos de comunicación
1. Registro de robot

El robot al iniciar envía:

{
  "from": "ROB4351",
  "type": "register",
  "timestamp": 1761674194575
}


El dispatcher responde:

{
  "robot_id": "ROB4351",
  "udp_port": 10023,
  "mesh_ports": {
    "ROB1001": 10010,
    "ROB1002": 10011
  }
}

2. Enviar comando a otro robot
{
  "from": "ROB4351",
  "to": "ROB3001",
  "type": "command",
  "command": "move",
  "value": "left",
  "timestamp": 1761674194575
}

3. Enviar datos de sensores
{
  "from": "ROB4351",
  "type": "sensor",
  "pos": [1.2, 3.4],
  "rotation": 90,
  "collision": false,
  "timestamp": 1761674194575
}

▶️ Ejemplo de ejecución básica

Iniciar dispatcher

node dispatcher.js


Iniciar dos robots

python robot_listener.py --id ROB1
python robot_listener.py --id ROB2


Enviar comando desde ROB1 a ROB2

python robot_mesh.py --from ROB1 --to ROB2 --cmd "move" --value "forward"


ROB2 recibe:

[UDP] from ROB1 → move: forward

🛣 Roadmap
✔️ MVP (este repositorio)

Asignación dinámica de puertos

Comunicación robot-robot

Comunicación robot-dispatcher

Mensajes JSON estándar

Timestamps

Python + Node operativos

🔜 Próxima etapa

Integrar frontend en Godot

Visualización en tiempo real

Sensores virtuales (posición, rotación, colisiones)

Control desde tablero docente

🔮 Futuro

Robots ESP32 físicos

Sincronización con WebRTC

Grid automatizado con 50+ robots

Persistencia de simulación

Integración con simulador Ester 5.0

📄 Licencia

MIT License – Universidad Abierta Interamericana (UAI) / LRFIA.