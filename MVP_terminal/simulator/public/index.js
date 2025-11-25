const canvas = document.getElementById("map");
const ctx = canvas.getContext("2d");
const robotList = document.getElementById("robotList");
const panelStatus = document.getElementById("panel_status");
const panelCollitions = document.getElementById("panel_collitions");

const camCanvas = document.getElementById("camCanvas");
const camCtx = camCanvas.getContext("2d");

const socket = io();

let robots = [];
let objects = [];
let collisions = [];
// client-side animation state per robot (persists across server updates)
const animState = {};

// Dimensiones base del mundo (se usan para escalar en fullscreen)
const BASE_W = canvas.width;
const BASE_H = canvas.height;

// Placeholder cámara
function drawCamPlaceholder(){
  camCtx.fillStyle="#222";
  camCtx.fillRect(0,0,camCanvas.width,camCanvas.height);
  camCtx.fillStyle="#fff";
  camCtx.font="16px sans-serif";
  camCtx.fillText("Futuro Canvas de Cámara",10,30);
}

// ===============================================
// TELEPORT MEJORADO CON FADE-IN SUAVE Y NOMBRE
// ===============================================
function teleportRobot(rb, targetX, targetY, targetRot) {
  const id = rb.id;
  animState[id] = animState[id] || {};
  const colorOrig = rb.color ? [...rb.color] : [200,200,200];

  const duration = 800; // ms de fade-in/out
  const frames = Math.round(duration / 16);
  const easeOut = t => 1 - Math.pow(1 - t, 3);

  // ==============================
  // 1️⃣ Halo breve en posición inicial
  // ==============================
  animState[id].hidden = false;
  animState[id].halo = true;
  animState[id].haloSize = 5;
  animState[id].showName = false;
  animState[id].appearing = false;
  animState[id].white = false;
  animState[id].alpha = 1;



  setTimeout(() => {
    // ==============================
    // 2️⃣ Desaparece todo
    // ==============================
    animState[id].hidden = true;
    animState[id].halo = false;

    // Reposicionar robot
    rb.x = targetX;
    rb.y = targetY;
    rb.rot = targetRot;

    // ==============================
    // 3️⃣ Halo en nueva posición + fade-in
    // ==============================
    animState[id].hidden = false;
    animState[id].halo = true;
    animState[id].haloSize = 5;
    animState[id].appearing = true;
    animState[id].white = true;
    animState[id].alpha = 0;
    animState[id].showName = false;
    animState[id].origColor = colorOrig;

    let frame = 0;
    const dx = 0; // ya está reposicionado
    const dy = 0;
    const drot = 0;

    const fadeIn = () => {
      if (!animState[id]) return;

      // fade-in
      animState[id].alpha = easeOut(frame / frames);

      // halo crece y desaparece
      animState[id].haloSize += 0.5;
      if (animState[id].haloSize > 20) animState[id].halo = false;

      // mostrar nombre cuando alpha > 0.5
      animState[id].showName = animState[id].alpha > 0.5;

      frame++;
      if (frame < frames) requestAnimationFrame(fadeIn);
      else {
        animState[id].appearing = false;
        animState[id].white = false;
        animState[id].showName = true;
        rb.color = [...colorOrig];
        appendStatus(`🛸 ${id} teletransportado a x=${Math.round(rb.x)}, y=${Math.round(rb.y)}, rot=${Math.round(rb.rot)}°`);
      }
    };

    fadeIn();

  }, 200); // duración breve del halo inicial antes de desaparecer
}



let currentScenario = 'futbol';
let rescueInfo = null;

socket.on("state_update", data => {
  objects = data.objects;
  collisions = data.collisions || [];
  currentScenario = data.scenario || currentScenario;
  rescueInfo = data.rescue || rescueInfo;

  // Normalizar robots: asignar id = name, x/y = pos[0]/pos[1]
  robots = data.robots.map(rb => ({
    id: rb.name || rb.id || "UNKNOWN",
    x: rb.pos ? rb.pos[0] : rb.x ?? 0,
    y: rb.pos ? rb.pos[1] : rb.y ?? 0,
    rot: rb.rot ?? 0,
    color: rb.color || [200,200,200],
    collision: rb.collision ?? false,
    cmd: rb.cmd,
    data: rb.data
  }));

  // inicializar animState si no existe
  robots.forEach(rb => { animState[rb.id] = animState[rb.id] || {}; });

  // procesar comandos
  robots.forEach(rb => {
    if (rb.cmd) {
      switch(rb.cmd) {
        case "teleport":
          teleportRobot(rb, rb.x, rb.y, rb.rot);
          break;
        case "move":
          if (rb.data?.dx) rb.x += rb.data.dx;
          if (rb.data?.dy) rb.y += rb.data.dy;
          if (rb.data?.drot) rb.rot = (rb.rot + rb.data.drot) % 360;
          appendStatus(`➡️ ${rb.id} movido dx=${rb.data?.dx||0}, dy=${rb.data?.dy||0}, drot=${rb.data?.drot||0}`);
          break;
        case "rotate":
          if (rb.data?.rot !== undefined) rb.rot = rb.data.rot;
          appendStatus(`🔄 ${rb.id} rotado a ${rb.rot}°`);
          break;
      }
      delete rb.cmd;
      delete rb.data;
    }
  });

  draw();
  updatePanel();
  drawCamPlaceholder();
});




 //recibe la salida de run_code
 socket.on('panel_output', line => {
  if (typeof panel_output !== "undefined" && panel_output)
    panel_output.textContent += line;
  if (typeof runBtn !== "undefined" && runBtn)
    runBtn.disabled = false;
});


function draw(){
  const scaleX = canvas.width / BASE_W;
  const scaleY = canvas.height / BASE_H;

  ctx.save();
  ctx.scale(scaleX, scaleY);
  // Fondo por escenario
  if(currentScenario==='futbol'){
    ctx.fillStyle = "#165616"; // verde césped
    ctx.fillRect(0,0,BASE_W,BASE_H);
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2 / Math.max(scaleX, scaleY);
    ctx.strokeRect(0,0,BASE_W,BASE_H);
    ctx.beginPath();
    ctx.moveTo(BASE_W/2, 0);
    ctx.lineTo(BASE_W/2, BASE_H);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(BASE_W/2, BASE_H/2, BASE_H/6, 0, 2*Math.PI);
    ctx.stroke();
    ctx.strokeRect(0, BASE_H/4, BASE_W*0.1, BASE_H/2);
    ctx.strokeRect(BASE_W*0.9, BASE_H/4, BASE_W*0.1, BASE_H/2);
  } else if(currentScenario==='laberinto') {
    // Piso amarillo claro
    ctx.fillStyle = "#ffe9a8";
    ctx.fillRect(0,0,BASE_W,BASE_H);
  } else if(currentScenario==='obstaculos') {
    // Fondo gris neutro suave (menos brillo)
    ctx.fillStyle = "#cfd2d3"; // puedes probar alternativas: #d4d6d8, #c7cbcc
    ctx.fillRect(0,0,BASE_W,BASE_H);
  }

  // dibujar objetos (las coordenadas ya están en el espacio base)
  for(const obj of objects){
    let fill = `rgb(${obj.color[0]},${obj.color[1]},${obj.color[2]})`;
    if(obj.role==='zone'){
      // revert: dibujar zona completa sin transparencia especial
      ctx.fillStyle = fill;
      ctx.fillRect(obj.x-obj.width/2, obj.y-obj.height/2, obj.width, obj.height);
    } else if(obj.name==='goal_center'){
      // resaltar goal con borde
      ctx.fillStyle = fill;
      ctx.fillRect(obj.x-obj.width/2, obj.y-obj.height/2, obj.width, obj.height);
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2 / Math.max(scaleX, scaleY);
      ctx.strokeRect(obj.x-obj.width/2, obj.y-obj.height/2, obj.width, obj.height);
      ctx.fillStyle = '#fff';
      ctx.font = '14px sans-serif';
      ctx.textAlign='center';
      ctx.textBaseline='middle';
      ctx.fillText('META', obj.x, obj.y);
    } else {
      ctx.fillStyle = fill;
      ctx.fillRect(obj.x-obj.width/2, obj.y-obj.height/2, obj.width, obj.height);
    }
  }

  // dibujar robots
for(const rb of robots){
  const x = rb.x;
  const y = rb.y;
  const rot = rb.rot || 0;
  const as = animState[rb.id] || {};

  if (as.hidden) continue; // no dibujar mientras oculto

  // determinar color y alpha
  const drawColor = (as.white) ? [255,255,255] : (rb.color || [200,200,200]);
  const drawAlpha = as.alpha !== undefined ? as.alpha : 1;

  ctx.save();
  ctx.globalAlpha = drawAlpha;

  // dibujar halo
  if (as.halo) {
    ctx.fillStyle = "rgb(255,255,0)";
    ctx.beginPath();
    ctx.arc(x, y, as.haloSize, 0, 2*Math.PI);
    ctx.fill();
  }

  // dibujar robot
  ctx.fillStyle = `rgb(${drawColor[0]},${drawColor[1]},${drawColor[2]})`;
  ctx.beginPath();
  ctx.arc(x, y, 10, 0, 2*Math.PI); // radio en coordenadas base
  ctx.fill();

  // dibujar dirección
  const dx = 15 * Math.cos(rot * Math.PI / 180);
  const dy = 15 * Math.sin(rot * Math.PI / 180);
  ctx.strokeStyle = "#ff0";
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + dx, y + dy);
  ctx.stroke();

  // dibujar nombre solo si showName
  // Asegurar fuente y dibujar nombre (siempre visible salvo hidden)
  if (as.showName === undefined) as.showName = true; // default: mostrar
  if (as.showName) {
    const fontSize = 12; // tamaño base
    ctx.font = `${fontSize}px sans-serif`;
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = "#ffffff";
    ctx.fillText(rb.id, x + 14, y - 14);
  }

  ctx.restore();
  }

  ctx.restore();
}


function updatePanel(){
  robotList.innerHTML = "";
  for(const rb of robots){
    const li = document.createElement("li");
    li.textContent = rb.id + (rb.collision?.collision?" (COL)":"");
    robotList.appendChild(li);
  }
  const rescueLine = (currentScenario==='rescate' && rescueInfo)? `<div style="color:#0af">Rescate: ${rescueInfo.placed}/${rescueInfo.total} ${rescueInfo.done? '✔️':''}</div>`:'';
  if(panelCollitions.style){ panelCollitions.style.background = '#111'; }
  panelCollitions.innerHTML = rescueLine + collisions.map(c=>`<div>${c}</div>`).join("");
  // toggle controles objetos según escenario
  const objCountInput = document.getElementById('objCount');
  const regenBtn = document.getElementById('regenBtn');
  if(objCountInput && regenBtn){
    const enabled = currentScenario==='obstaculos';
    objCountInput.disabled = !enabled;
    regenBtn.disabled = !enabled;
  }
}

 function appendStatus(msg) {
    const timestamp = new Date().toLocaleTimeString();
    if (panelStatus) {
     // panelStatus.textContent += `${timestamp}> ${msg}\n`;
      panelStatus.textContent += `\n${msg}`;
      panelStatus.scrollTop = panelStatus.scrollHeight;
    } else {
      console.log(`${timestamp}> ${msg}`);
    }
  }

// botones
document.getElementById("regenBtn").onclick = () => {
  const inputValue = document.getElementById("objCount").value;
  // parseInt convierte "0" en 0, pero no usar || aquí
  let count = parseInt(inputValue, 10);
  // Si el usuario dejó vacío o puso algo no numérico
  if (isNaN(count)) count = 50;
  // Solo los negativos se convierten en -1
  if (count < 0) count = -1;

  //console.log("Enviando count:", count); // para probar
  fetch(`/regenerate/${count}`);
};

window.clearEditor = function clearEditor() {
    if (confirm("¿Seguro que querés limpiar el editor de código?")) {
      window.editor.setValue('');
      const panelOutput = document.getElementById('panel_output');
      if (panelOutput) panelOutput.textContent = '';
      panelStatus.textContent = '';
    }
  };

window.clearOutput = function clearOutput() {
    const panelOutput = document.getElementById("panel_output");
    if (panelOutput) panelOutput.textContent = '';
  };

  // ==============================
  // ✍️ Editor Monaco
  // ==============================
  require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs' } });
  require(['vs/editor/editor.main'], function () {
    window.editor = monaco.editor.create(document.getElementById('editor'), {
      value: "// Esperando código...",
      language: "python",
      theme: "vs-dark",
      fontSize: 14,
      automaticLayout: true,
      minimap: { enabled: false }
    });
  });

   // ==============================
  // 🚀 Ejecución de código remoto
  // ==============================
  window.runCode = function runCode() {
    const runBtn = document.getElementById('runBtn');
    const panelOutput = document.getElementById('panel_output');

    //if (runBtn) runBtn.disabled = true;
    if (panelStatus) panelStatus.textContent = '';
    if (panelOutput) panelOutput.textContent = '';

    const code = window.editor ? window.editor.getValue().trim() : '';

    if (!code) {
      appendStatus("⚠️ El código está vacío.");
      if (runBtn) runBtn.disabled = false;
      return;
    }

    socket.emit('run_code', { code });
    appendStatus(`🚀 Código enviado al robot`);
    if (runBtn) runBtn.disabled = false;
  };

  window.addEventListener('DOMContentLoaded', () => {
  const runBtn = document.getElementById('runBtn');
  if (runBtn) runBtn.addEventListener('click', () => {
    if (window.runCode) window.runCode();
  });
});

  // ==============================
  // 🖥️ Pantalla completa del canvas del simulador (doble click)
  // ==============================
  let originalCanvasSize = { w: canvas.width, h: canvas.height };

  function enterSimFullscreen(){
    originalCanvasSize = { w: canvas.width, h: canvas.height };
    // Ajustar tamaño real del canvas al viewport
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    canvas.style.width = '100vw';
    canvas.style.height = '100vh';
    appendStatus('🖥️ Canvas simulador en pantalla completa');
    draw();
  }

  function exitSimFullscreen(){
    // Restaurar tamaño original
    canvas.width = originalCanvasSize.w;
    canvas.height = originalCanvasSize.h;
    canvas.style.width = '';
    canvas.style.height = '';
    appendStatus('↩️ Canvas simulador fuera de pantalla completa');
    draw();
  }

  function toggleSimFullscreen(){
    if (!document.fullscreenElement){
      if (canvas.requestFullscreen){
        canvas.requestFullscreen().then(()=>enterSimFullscreen()).catch(()=>enterSimFullscreen());
      } else {
        enterSimFullscreen();
      }
    } else {
      if (document.exitFullscreen){
        document.exitFullscreen().then(()=>exitSimFullscreen()).catch(()=>exitSimFullscreen());
      } else {
        exitSimFullscreen();
      }
    }
  }

  canvas.addEventListener('dblclick', toggleSimFullscreen);
  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement){
      // Al salir por ESC
      exitSimFullscreen();
    }
  });

  window.addEventListener('resize', () => {
    // Si seguimos en fullscreen, ajustar a nuevo tamaño
    if (document.fullscreenElement === canvas){
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      draw();
    }
  });

  // Escenario selector
  const scenarioSelect = document.getElementById('scenarioSelect');
  if(scenarioSelect){
    scenarioSelect.addEventListener('change', e=>{
      const val = e.target.value;
      fetch(`/scenario/${val}`).then(()=>appendStatus(`🗺️ Escenario cambiado a ${val}`)).catch(()=>appendStatus('⚠️ Error cambiando escenario'));
    });
  }

// ==============================
  // 📂 Cargar ejemplo Python en el editor (selector de ejemplos)
  // ==============================
  const selectorEjemplo = document.getElementById("selector");

  if (selectorEjemplo) {
    selectorEjemplo.addEventListener("change", async (e) => {
      const nombre = e.target.value;
      if (!nombre) return; // Si no se seleccionó nada, no hace nada

      try {
        let url = `/examples/${nombre}`;
        if (!url.endsWith(".py")) url += ".py"; // permite omitir la extensión

        const res = await fetch(url);
        if (!res.ok) {
          appendStatus(`❌ No se encontró el ejemplo: ${nombre}`);
          return;
        }

        const code = await res.text();
        if (window.editor) {
          window.editor.setValue(code);
          appendStatus(`📄 Ejemplo cargado: ${nombre}`);
        }
      } catch (err) {
        appendStatus(`⚠️ Error cargando ${nombre}: ${err.message}`);
      }
    });
  }
