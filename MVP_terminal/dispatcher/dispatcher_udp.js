// ===============================================
// Dispatcher Socket.IO + UDP con reenvío a simulador
// Node.js
// ===============================================
import express from "express";
import http from "http";
import { Server } from "socket.io";
import dgram from "dgram";

const app = express();
const server = http.createServer(app);
const io = new Server(server);

const BASE_UDP_SEND = 10010;  // dispatcher recibe del robot
const BASE_UDP_RECV = 11010;  // dispatcher envía al robot
const MAX_ROBOTS = 60;

// Configuración del simulador
const UDP_DISPATCHER_TO_SIM = 10009; // puerto del simulador
const SIM_HOST = "127.0.0.1";

let nextIndex = 0;
const robots = {}; // id -> { sendPort, recvPort, udpSocket }

server.listen(6029, () => console.log("Dispatcher Socket.IO escuchando en puerto 6029"));

// Asignación de puertos al conectar
io.on("connection", (socket) => {
  console.log("Nuevo robot conectado:", socket.id);

  const index = nextIndex++;
  const sendPort = BASE_UDP_SEND + index; // puerto donde dispatcher recibe
  const recvPort = BASE_UDP_RECV + index; // puerto donde dispatcher envía

  // UDP socket para recibir datos del robot
  const udpSocket = dgram.createSocket("udp4");
  udpSocket.on("message", (msg, rinfo) => {
    try {
      const packet = JSON.parse(msg.toString());
      console.log(`[${packet.src}] Recibido en dispatcher UDP ${sendPort}:`, packet);

      // --- REENVÍO AL SIMULADOR ---
      udpSocket.send(msg, UDP_DISPATCHER_TO_SIM, SIM_HOST, (err) => {
        if (err) console.log(`Error reenviando a simulador: ${err}`);
      });

    } catch (e) {
      console.log("Error parseando paquete UDP:", e);
    }
  });

  udpSocket.bind(sendPort, () => {
    console.log(`[DISPATCHER] Escuchando robot ${socket.id} en UDP ${sendPort}`);
  });

  robots[socket.id] = { sendPort, recvPort, udpSocket };
  socket.emit("udp_ports", { send: sendPort, recv: recvPort });

  socket.on("disconnect", () => {
    console.log(`[DISPATCHER] Robot desconectado: ${socket.id}, puertos liberados`);
    udpSocket.close();
    delete robots[socket.id];
  });
});
