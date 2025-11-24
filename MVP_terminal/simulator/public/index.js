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

// Placeholder cámara
function drawCamPlaceholder(){
  camCtx.fillStyle="#222";
  camCtx.fillRect(0,0,camCanvas.width,camCanvas.height);
  camCtx.fillStyle="#fff";
  camCtx.font="16px sans-serif";
  camCtx.fillText("Futuro Canvas de Cámara",10,30);
}

socket.on("state_update", data=>{
  robots = data.robots;
  objects = data.objects;
  collisions = data.collisions || [];
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

  // objetos
  for(const obj of objects){
    ctx.fillStyle = `rgb(${obj.color[0]},${obj.color[1]},${obj.color[2]})`;
    ctx.fillRect(obj.x-obj.width/2,obj.y-obj.height/2,obj.width,obj.height);
  }

  // robots
  for(const rb of robots){
    ctx.fillStyle = `rgb(${rb.color[0]},${rb.color[1]},${rb.color[2]})`;
    ctx.beginPath();
    ctx.arc(rb.x, rb.y, 10,0,2*Math.PI);
    ctx.fill();

    // orientación
    const dx = 15 * Math.cos(rb.rot||0);
    const dy = 15 * Math.sin(rb.rot||0);
    ctx.strokeStyle = "#ff0";
    ctx.beginPath();
    ctx.moveTo(rb.x, rb.y);
    ctx.lineTo(rb.x+dx, rb.y+dy);
    ctx.stroke();

    // nombre siempre visible
    ctx.fillStyle="#fff";
    ctx.fillText(rb.id, rb.x+12, rb.y-12);
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

  console.log("Enviando count:", count); // para probar
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
