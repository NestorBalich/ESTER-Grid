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
const robots = {}; // { robot_id: { name,x,y,tx,ty,rot,last_seen,alpha,color,collision,cmd,data,distance,collisions_count } }
let objects = [];
let scenarioType = 'futbol'; // futbol | laberinto | obstaculos
let rescueProgress = { placed: 0, total: 0, done: false };

// ----------------------------
// Logging helpers
// ----------------------------
const logsDir = `${__dirname}/../logs`;
const eventsLog = `${logsDir}/events.log`;
if(!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });

function logEvent(type, payload){
  const line = JSON.stringify({ ts: Date.now(), type, ...payload });
  fs.appendFile(eventsLog, line+"\n", ()=>{});
}

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

function generate_labyrinth(){
  objects = [];
  const wallColor = [213,106,0]; // naranja ladrillo
  const borderThickness = 16;
  // Maze dimensions (cells)
  const cols = 14; // adjust for width
  const rows = 10; // adjust for height
  const cellW = WINDOW_W / cols;
  const cellH = WINDOW_H / rows;

  // Maze generation (recursive backtracker)
  const visited = Array.from({length: rows}, () => Array(cols).fill(false));
  // walls arrays: vertical walls between cells (cols+1 x rows), horizontal walls (cols x rows+1)
  const vWalls = Array.from({length: rows}, () => Array(cols+1).fill(true));
  const hWalls = Array.from({length: rows+1}, () => Array(cols).fill(true));

  function shuffle(arr){ for(let i=arr.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [arr[i],arr[j]]=[arr[j],arr[i]];} return arr; }
  function carve(r,c){
    visited[r][c]=true;
    const dirs = shuffle([[0,1],[0,-1],[1,0],[-1,0]]);
    for(const [dr,dc] of dirs){
      const nr=r+dr, nc=c+dc;
      if(nr<0||nr>=rows||nc<0||nc>=cols||visited[nr][nc]) continue;
      // remove wall between (r,c) and (nr,nc)
      if(dr===0){ // horizontal move -> vertical wall removed
        if(dc===1) vWalls[r][c+1]=false; else vWalls[r][c]=false;
      } else { // vertical move -> horizontal wall removed
        if(dr===1) hWalls[r+1][c]=false; else hWalls[r][c]=false;
      }
      carve(nr,nc);
    }
  }
  carve(0,0); // start at entrance cell (top-left)

  // Create outer border walls, leaving entrance at left and exit near center or right
  // Entrance: gap at (0,0) left boundary. Exit: gap at center cell outer boundary toward center objective.
  // We'll leave gap on outer left for row 0 and outer right for row Math.floor(rows/2).

  // Build walls as objects
  // Horizontal walls
  for(let r=0;r<=rows;r++){
    for(let c=0;c<cols;c++){
      if(hWalls[r][c]){
        // skip gap for entrance (r===0 && c===0)
        // skip gap for exit (r===Math.floor(rows/2) && c===cols-1)
        if(r===0 && c===0) continue;
        if(r===Math.floor(rows/2) && c===cols-1) continue;
        const x = c*cellW + cellW/2;
        const y = r*cellH;
        objects.push({ x, y, type:'inamovible', name:`h_${r}_${c}`, color:wallColor, width: cellW, height: borderThickness });
      }
    }
  }
  // Vertical walls
  for(let r=0;r<rows;r++){
    for(let c=0;c<=cols;c++){
      if(vWalls[r][c]){
        // skip gap for entrance (r===0 && c===0)
        if(r===0 && c===0) continue;
        // skip gap for exit (r===Math.floor(rows/2) && c===cols)
        if(r===Math.floor(rows/2) && c===cols) continue;
        const x = c*cellW;
        const y = r*cellH + cellH/2;
        objects.push({ x, y, type:'inamovible', name:`v_${r}_${c}`, color:wallColor, width: borderThickness, height: cellH });
      }
    }
  }

  // Goal object at center
  const goalX = WINDOW_W/2;
  const goalY = WINDOW_H/2;
  objects.push({ x: goalX, y: goalY, type:'inamovible', name:'goal_center', color:[0,200,0], width: 30, height: 30 });
}

function setScenario(type){
  if(!['futbol','laberinto','obstaculos','rescate'].includes(type)) return;
  scenarioType = type;
  if(type==='futbol'){
    objects = []; // cancha sin obstáculos
  } else if(type==='laberinto'){
    generate_labyrinth();
  } else if(type==='obstaculos'){
    generate_objects(50);
  } else if(type==='rescate'){
    generate_rescue();
  }
  console.log('Scenario cambiado a', scenarioType, 'objetos=', objects.length);
}

// ----------------------------
// Escenario Rescate
// ----------------------------
function generate_rescue(){
  objects = [];
  rescueProgress = { placed: 0, total: 0, done: false };
  // Zonas oscuras
  const zoneColors = {
    red: [139,0,0],      // rojo oscuro
    green: [0,100,0],    // verde oscuro
    blue: [0,0,139]      // azul oscuro
  };
  // Objetos claros
  const itemColors = {
    red: [255,150,150],   // rojo claro
    green: [144,238,144], // verde claro
    blue: [135,206,250]   // azul claro
  };
  // Tres zonas verticales (tercios)
  const zoneWidth = WINDOW_W / 3;
  const zoneHeight = WINDOW_H;
  const zones = [
    { key:'red',   name:'zone_red',   x: zoneWidth*0.5, y: WINDOW_H/2 },
    { key:'green', name:'zone_green', x: zoneWidth*1.5, y: WINDOW_H/2 },
    { key:'blue',  name:'zone_blue',  x: zoneWidth*2.5, y: WINDOW_H/2 }
  ];
  for(const z of zones){
    objects.push({ x:z.x, y:z.y, type:'zona', name:z.name, color: zoneColors[z.key], width:zoneWidth, height:zoneHeight, role:'zone', zoneColor:itemColors[z.key] });
  }
  // 3 objetos movibles de cada color (total 9)
  const itemSize = 20;
  for(const ckey of ['red','green','blue']){
    const col = itemColors[ckey];
    for(let i=0; i<3; i++){
      const x = 100 + Math.random()*(WINDOW_W-200);
      const y = 50 + Math.random()*(WINDOW_H-100);
      objects.push({ x, y, type:'movible', name:`item_${ckey}_${i}`, color: col, width:itemSize, height:itemSize, role:'item', targetColor: col });
    }
  }
  rescueProgress.total = 9;
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

    const name = packet.name || packet.data?.name || rid;
    if (!robots[rid]) {
      robots[rid] = { name, x: px, y: py, tx: px, ty: py, rot, last_seen: Date.now()/1000, alpha: 255, color, collision: {collision:false}, cmd:null, data:null, distance:0, collisions_count:0 };
      logEvent('robot_join', { id: rid, name, x: px, y: py });
    } else {
      // allow dynamic rename if provided
      robots[rid].name = name;
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
      logEvent('teleport', { id: rid, name: rb.name, x: rb.x, y: rb.y, rot: rb.rot });
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
        logEvent('cmd', { id: rid, name: rb.name, cmd, data: cmdData });
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
// Escenario endpoint
// ----------------------------
app.get('/scenario/:type', (req,res)=>{
  const t = req.params.type;
  setScenario(t);
  res.json({ ok:true, scenario: scenarioType, objects: objects.length });
});

// ----------------------------
// Movimiento y colisiones
// ----------------------------
function apply_movement(rb){
  let dx = rb.tx - rb.x;
  let dy = rb.ty - rb.y;
  const dist = Math.sqrt(dx*dx+dy*dy);
  if(dist===0) return [false,null,0];

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
      else { return [false, collision_info, 0]; }
    }
  }

  rb.x += move_dx; rb.y += move_dy;
  const movedDist = Math.sqrt(move_dx*move_dx + move_dy*move_dy);
  return [true, collision_info, movedDist];
}

function updateRescueProgress(){
  if(scenarioType!=='rescate') return;
  let placed = 0;
  // identify zones
  const zones = objects.filter(o=>o.role==='zone');
  const items = objects.filter(o=>o.role==='item');
  for(const it of items){
    for(const z of zones){
      if(it.targetColor[0]===z.zoneColor[0] && it.targetColor[1]===z.zoneColor[1] && it.targetColor[2]===z.zoneColor[2]){
        // check inside zone rectangle
        const insideX = Math.abs(it.x - z.x) <= z.width/2 - it.width/2;
        const insideY = Math.abs(it.y - z.y) <= z.height/2 - it.height/2;
        if(insideX && insideY){ placed++; }
        break;
      }
    }
  }
  rescueProgress.placed = placed;
  if(placed === rescueProgress.total && !rescueProgress.done){
    rescueProgress.done = true;
    logEvent('rescate_completed', { total: rescueProgress.total });
  }
}

// ----------------------------
// Broadcast estado a clientes WebSocket
// ----------------------------
setInterval(()=>{
  const now = Date.now()/1000;
  const collisions = [];

  for(const rid in robots){
    const rb = robots[rid];
    const [moved, collision, distMoved] = apply_movement(rb);
    if(moved && distMoved>0){ rb.distance += distMoved; }
    if(now - rb.last_seen > TIMEOUT_SEC) rb.alpha -= FADE_SPEED*255;
    if(rb.alpha<0) rb.alpha=0;

    if(collision){
      rb.collision = collision;
      collisions.push(`${rid} chocó con ${collision.name}`);
      rb.collisions_count += 1;
      logEvent('collision', { id: rid, name: rb.name, with: collision.name, type: collision.type });
    } else {
      rb.collision = {collision:false};
    }

    if(now - rb.last_seen > 10){
      delete robots[rid];
      console.log(`Robot ${rid} eliminado por inactividad.`);
      logEvent('robot_leave', { id: rid });
    }
  }

  updateRescueProgress();

  io.emit("state_update",{
    robots: Object.entries(robots).map(([rid,rb])=>({
      id: rid,
      name: rb.name,
      x: rb.x, y: rb.y, tx: rb.tx, ty: rb.ty, rot: rb.rot,
      alpha: rb.alpha, color: rb.color, collision: rb.collision,
      distance: rb.distance, collisions_count: rb.collisions_count,
      cmd: rb.cmd, data: rb.data
    })),
    objects,
    collisions,
    scenario: scenarioType,
    rescue: rescueProgress
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

// ----------------------------
// Metrics endpoint
// ----------------------------
app.get('/metrics', (req,res)=>{
  const summary = {
    ts: Date.now(),
    robots: Object.entries(robots).map(([rid,rb])=>({ id: rid, name: rb.name, x: rb.x, y: rb.y, rot: rb.rot, distance: rb.distance, collisions: rb.collisions_count })),
    robots_count: Object.keys(robots).length,
    total_distance: Object.values(robots).reduce((a,r)=>a+r.distance,0),
    total_collisions: Object.values(robots).reduce((a,r)=>a+r.collisions_count,0)
  };
  res.json(summary);
});
