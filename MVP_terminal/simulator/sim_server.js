// ========================================================
// ESTER-GRID Node.js Server v8 - UDP ↔ WebSocket con Dispatcher
// Múltiples robots, GPS, colisión, fade-out, teleport
// ========================================================

import dgram from "dgram";
import express from "express";
import http from "http";
import { Server } from "socket.io";
import fs from "fs";
import { spawn } from "child_process";

import { fileURLToPath } from "url";
const __dirname = fileURLToPath(new URL('.', import.meta.url));

const cfgPath = `${__dirname}/../config.json`;
const cfg = JSON.parse(fs.readFileSync(cfgPath));

const UDP_DISPATCHER_TO_SIM = cfg.udp_dispatcher_to_sim || 10009; // paquetes del dispatcher
const UDP_SIM_TO_DISPATCHER = cfg.udp_sim_to_dispatcher || 10008; // respuesta sim → dispatcher
const UDP_HOST = "0.0.0.0";
const HTTP_PORT = cfg.http_port || 4001;

const WINDOW_W = 900;
const WINDOW_H = 600;
const TIMEOUT_SEC = 2;
const FADE_SPEED = 0.05;
const ROBOT_SIZE = 10;
const ROBOT_SPEED = 2.0;
const OBJ_WIDTH = 25;
const OBJ_HEIGHT = 15;

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.static("public"));

// ----------------------------
// UDP Socket
// ----------------------------
const sock = dgram.createSocket("udp4");
const robots = {}; // { robot_id: { x,y,tx,ty,rot,last_seen,alpha,color,collision,cmd,data } }
let objects = [];

// ----------------------------
// Helpers
// ----------------------------
function clamp_pos(x, y) {
  x = Math.max(0, Math.min(WINDOW_W, x));
  y = Math.max(0, Math.min(WINDOW_H, y));
  return [x, y];
}

function robot_color(rid) {
  const seed = Array.from(rid).reduce((a, b) => a + b.charCodeAt(0), 0);
  return [(seed * 50) % 255, (seed * 80) % 255, (seed * 110) % 255];
}

function generate_objects(count = 50) {
  objects = [];
  if (count <= 0) {
    objects.push({ x: -100, y: -100, type: "inamovible", name: "out_0", color: [0,0,0], width: OBJ_WIDTH, height: OBJ_HEIGHT });
    return;
  }
  for (let i = 0; i < count; i++) {
    const obj_type = Math.random() > 0.5 ? "movible" : "inamovible";
    const obj_name = `${obj_type.slice(0,3)}_${i}`;
    const x = 50 + Math.random() * (WINDOW_W - 100);
    const y = 50 + Math.random() * (WINDOW_H - 100);
    const color = obj_type === "inamovible"
      ? [255,0,0]
      : [Math.random()*205+50, Math.random()*205+50, Math.random()*205+50];
    objects.push({ x, y, type: obj_type, name: obj_name, color, width: OBJ_WIDTH, height: OBJ_HEIGHT });
  }
}

// ----------------------------
// UDP Receiver (solo del dispatcher)
// ----------------------------
sock.on("message", (msg, rinfo) => {
  try {
    const packet = JSON.parse(msg.toString());
    if (packet.type !== "state") return;

    const rid = packet.src;
    if(!rid) return;

    console.log(`[UDP] Paquete recibido de ${rid} desde ${rinfo.address}:${rinfo.port}`);
    console.log(packet.data); // opcional: mostrar datos completos del robot

    // --- resto de tu código existente ---
    let px = 0, py = 0;
    if (Array.isArray(packet.data.pos)) {
      if (packet.data.pos.length === 3) {
        px = packet.data.pos[0];
        py = packet.data.pos[2];
      } else if (packet.data.pos.length >= 2) {
        px = packet.data.pos[0];
        py = packet.data.pos[1];
      }
    }
    [px, py] = clamp_pos(px, py);

    const rot = packet.data.rot || 0;
    const color = packet.data.color || robot_color(rid);

    const cmd = packet.cmd || packet.data?.cmd || null;
    const cmdData = packet.cmdData || packet.data || null;

    if (!robots[rid]) {
      robots[rid] = { x: px, y: py, tx: px, ty: py, rot, last_seen: Date.now()/1000, alpha: 255, color, collision: {collision:false}, cmd:null, data:null };
    }

    const rb = robots[rid];

    if (cmd === 'teleport') {
      rb.x = px;
      rb.y = py;
      rb.tx = px;
      rb.ty = py;
      if(cmdData && cmdData.rot!==undefined) rb.rot = cmdData.rot;
      rb.last_seen = Date.now()/1000;
      rb.alpha = 255;
      rb.color = color;
      rb.cmd = 'teleport';
      rb.data = { x:px, y:py, rot:rb.rot };
    } else {
      rb.tx = px;
      rb.ty = py;
      rb.rot = rot;
      rb.last_seen = Date.now()/1000;
      rb.alpha = 255;
      rb.color = color;
      if(cmd){
        rb.cmd = cmd;
        rb.data = cmdData;
      }
    }

  } catch(e){
    console.log("Error UDP:", e);
  }
});


sock.bind(UDP_DISPATCHER_TO_SIM, UDP_HOST, () => {
  console.log("UDP server listening on", UDP_HOST, UDP_DISPATCHER_TO_SIM);
});

// ----------------------------
// Movimiento y colisiones
// ----------------------------
function apply_movement(rb){
  let dx = rb.tx - rb.x;
  let dy = rb.ty - rb.y;
  const dist = Math.sqrt(dx*dx+dy*dy);
  if(dist===0) return [false,null];

  const move_dx = dx/dist * Math.min(dist,ROBOT_SPEED);
  const move_dy = dy/dist * Math.min(dist,ROBOT_SPEED);
  let collision_info = null;

  for(const obj of objects){
    const dist_x = Math.abs(rb.x+move_dx - obj.x);
    const dist_y = Math.abs(rb.y+move_dy - obj.y);
    const overlap_x = (ROBOT_SIZE + obj.width/2) - dist_x;
    const overlap_y = (ROBOT_SIZE + obj.height/2) - dist_y;
    if(overlap_x>0 && overlap_y>0){
      collision_info = {collision:true,type:obj.type,name:obj.name};
      if(obj.type==="movible"){ obj.x += move_dx; obj.y += move_dy; }
      else { return [false, collision_info]; }
    }
  }

  rb.x += move_dx; rb.y += move_dy;
  return [true, collision_info];
}

// ----------------------------
// Broadcast estado a clientes WebSocket
// ----------------------------
setInterval(()=>{
  const now = Date.now()/1000;
  const collisions = [];

  for(const rid in robots){
    const rb = robots[rid];
    const [moved, collision] = apply_movement(rb);
    if(now - rb.last_seen > TIMEOUT_SEC) rb.alpha -= FADE_SPEED*255;
    if(rb.alpha<0) rb.alpha=0;

    if(collision){
      rb.collision = collision;
      collisions.push(`${rid} chocó con ${collision.name}`);
    } else {
      rb.collision = {collision:false};
    }

    if(now - rb.last_seen > 10){
      delete robots[rid];
      console.log(`Robot ${rid} eliminado por inactividad.`);
    }
  }

  io.emit("state_update",{
    robots: Object.entries(robots).map(([rid,rb])=>({
      id: rid,
      x: rb.x, y: rb.y, tx: rb.tx, ty: rb.ty, rot: rb.rot,
      alpha: rb.alpha, color: rb.color, collision: rb.collision,
      cmd: rb.cmd, data: rb.data
    })),
    objects,
    collisions
  });

  for(const rid in robots){ robots[rid].cmd = null; robots[rid].data = null; }

},50);

// ----------------------------
// WebSocket cliente (ejecución Python)
io.on('connection', socket=>{
  console.log('Cliente conectado:', socket.id);

  socket.on('run_code',({code})=>{
    const tempFile = `temp_${socket.id}.py`;
    const finalCode = `import sys\nsys.stdout.reconfigure(encoding='utf-8')\n${code}`;
    fs.writeFile(tempFile,finalCode,(err)=>{
      if(err) return socket.emit('panel_output','❌ Error al guardar archivo.\n');

      const pythonCmd = process.platform==='win32'?'python':'python3';
      const pyProcess = spawn(pythonCmd,[tempFile]);

      const timeout = setTimeout(()=>{
        pyProcess.kill();
        socket.emit('panel_output','⏱️ Tiempo de ejecución agotado (60s).\n');
        fs.unlink(tempFile,()=>{});
      },60000);

      pyProcess.stdout.on('data',(data)=>socket.emit('panel_output',data.toString()));
      pyProcess.stderr.on('data',(data)=>socket.emit('panel_output',`❌ Error: ${data.toString()}`));
      pyProcess.on('close',(code)=>{
        clearTimeout(timeout);
        fs.unlink(tempFile,()=>{});
        socket.emit('panel_output',`\n✔️ Proceso terminado con código ${code}\n`);
      });
    });
  });
});

// ----------------------------
// HTTP + regenerar objetos
app.get("/regenerate/:count",(req,res)=>{
  let count = parseInt(req.params.count,10);
  if(isNaN(count)) count = 50;
  generate_objects(count);
  res.json({ok:true,count});
});

server.listen(HTTP_PORT,()=>console.log("HTTP+WS server running on port",HTTP_PORT));
