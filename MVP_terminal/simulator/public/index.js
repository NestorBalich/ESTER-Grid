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



socket.on("state_update", data => {
  objects = data.objects;
  collisions = data.collisions || [];

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
  // dibujar cancha de fútbol
  ctx.fillStyle = "#165616ff"; // verde césped
  ctx.fillRect(0,0,canvas.width,canvas.height);

  // líneas de cancha (proporción simple)
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 2;

  // líneas de borde
  ctx.strokeRect(0,0,canvas.width,canvas.height);

  // línea central
  ctx.beginPath();
  ctx.moveTo(canvas.width/2, 0);
  ctx.lineTo(canvas.width/2, canvas.height);
  ctx.stroke();

  // círculo central
  ctx.beginPath();
  ctx.arc(canvas.width/2, canvas.height/2, canvas.height/6, 0, 2*Math.PI);
  ctx.stroke();

  // áreas de gol (simplificado)
  ctx.strokeRect(0, canvas.height/4, canvas.width*0.1, canvas.height/2);
  ctx.strokeRect(canvas.width*0.9, canvas.height/4, canvas.width*0.1, canvas.height/2);

  // dibujar objetos
  for(const obj of objects){
    ctx.fillStyle = `rgb(${obj.color[0]},${obj.color[1]},${obj.color[2]})`;
    ctx.fillRect(obj.x-obj.width/2,obj.y-obj.height/2,obj.width,obj.height);
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
  ctx.arc(x, y, 10, 0, 2*Math.PI);
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
  if (as.showName) {
    ctx.fillStyle = "#fff";
    ctx.fillText(rb.id, x+12, y-12);
  }

  ctx.restore();
}


}

function updatePanel(){
  robotList.innerHTML = "";
  for(const rb of robots){
    const li = document.createElement("li");
    li.textContent = rb.id + (rb.collision?.collision?" (COL)":"");
    robotList.appendChild(li);
  }
  panelCollitions.innerHTML = collisions.map(c=>`<div>${c}</div>`).join("");
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
