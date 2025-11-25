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
const UDP_MSG_PORT = 10011;   // puerto único para mensajes directos entre robots

// Configuración del simulador
const UDP_DISPATCHER_TO_SIM = 10009; // puerto del simulador
const SIM_HOST = "127.0.0.1";

let nextIndex = 0;
const robots = {}; // socket.id -> { sendPort, recvPort, udpSocket }
const udpEndpoints = {}; // robotId/name -> { address, port, lastSeen }

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

// ===============================================
// Mensajería UDP directa entre robots (router simple)
// ===============================================
const udpMsgSocket = dgram.createSocket("udp4");

function sendUdpJson(address, port, obj){
  try {
    const buf = Buffer.from(JSON.stringify(obj));
    udpMsgSocket.send(buf, port, address, (err)=>{
      if(err) console.log(`[MSG] Error enviando a ${address}:${port} ->`, err.message);
    });
  } catch(e){
    console.log("[MSG] Error serializando JSON:", e.message);
  }
}

udpMsgSocket.on("message", (msg, rinfo) => {
  let packet;
  try { packet = JSON.parse(msg.toString()); }
  catch(e){ console.log("[MSG] Paquete inválido:", e.message); return; }

  const src = packet.src || packet.from || packet.name;
  if(!src){
    // src requerido para registrar endpoint o enrutar
    sendUdpJson(rinfo.address, rinfo.port, { type: "error", code: "missing_src", message: "Se requiere 'src' en el paquete." });
    return;
  }

  // Registrar/actualizar endpoint del remitente
  udpEndpoints[src] = { address: rinfo.address, port: rinfo.port, lastSeen: Date.now() };

  if(packet.type === "register"){
    // Confirmar registro
    sendUdpJson(rinfo.address, rinfo.port, { type: "ack", src: "dispatcher", for: src });
    console.log(`[MSG] Registro endpoint ${src} -> ${rinfo.address}:${rinfo.port}`);
    return;
  }

  if(packet.type === "msg" || packet.type === "reply"){
    const to = packet.to || packet.dest || packet.target;
    if(!to){
      sendUdpJson(rinfo.address, rinfo.port, { type: "error", src: "dispatcher", code: "missing_to", message: "Se requiere 'to' en el paquete." });
      return;
    }
    const dest = udpEndpoints[to];
    if(!dest){
      sendUdpJson(rinfo.address, rinfo.port, { type: "error", src: "dispatcher", code: "unknown_target", message: `Destino '${to}' no registrado.` });
      return;
    }
    // Reenviar tal cual, agregando metadata mínima
    const mid = packet.mid || packet.id || `${Date.now()}_${Math.random().toString(36).slice(2,8)}`;
    const out = { ...packet, mid, via: "dispatcher" };
    sendUdpJson(dest.address, dest.port, out);
    return;
  }

  if(packet.type === "broadcast"){
    const out = { ...packet, via: "dispatcher" };
    Object.values(udpEndpoints).forEach(ep => sendUdpJson(ep.address, ep.port, out));
    return;
  }

  // Desconocido: notificar
  sendUdpJson(rinfo.address, rinfo.port, { type: "error", src: "dispatcher", code: "unknown_type", message: `Tipo '${packet.type}' no soportado.` });
});

udpMsgSocket.on("listening", ()=>{
  const addr = udpMsgSocket.address();
  console.log(`[MSG] Router de mensajes escuchando en ${addr.address}:${addr.port}`);
});

udpMsgSocket.on("error", (err)=>{
  console.log("[MSG] Error socket UDP mensajes:", err.message);
});

udpMsgSocket.bind(UDP_MSG_PORT, () => {
  // bound
});
