// ===============================================
// ESTER-Grid Dispatcher (EGUP v2)
// Node.js - UDP Router + Registry + Command API
// ===============================================

import dgram from "dgram";
import express from "express";
import fs from "fs";

const app = express();
app.use(express.json());

// Load configuration (MVP_terminal/config.json)
const cfgPath = new URL("../config.json", import.meta.url);
const cfg = JSON.parse(fs.readFileSync(cfgPath));

// ------------------------------------------
// UDP PORTS (configurable)
const UDP_BASE = cfg.udp_base || 10010;
const MAX_ROBOTS = 30; // hasta 30 robots

// robots: ROB1..ROB30 con puerto fijo para robot y gemelo digital
const robots = {}; // { ROBx: { port_robot, port_twin, address, last_state, last_ts } }
for (let i = 1; i <= MAX_ROBOTS; i++) {
    const name = `ROB${i}`;
    robots[name] = {
        port_robot_sim: UDP_BASE + (i - 1),
        port_robot_real: UDP_BASE + MAX_ROBOTS + (i - 1),
        address: null,
        last_state: null,
        last_ts: null
    };
}

// UDP socket para router
const dispatchSock = dgram.createSocket("udp4");

// ------------------------------------------
// HTTP: Registrar robot y dar puertos fijos
app.post("/register", (req, res) => {
    const { robotName } = req.body; // ROB1..ROB30
    if (!robotName || !robots[robotName]) {
        return res.status(400).json({ error: "robotName must be ROB1..ROB30" });
    }

    const r = robots[robotName];
    // Siempre devuelve sus puertos fijos, aunque no esté conectado aún
    res.json({
        robotName,
        port_robot_sim: r.port_robot_sim,
        port_robot_real   : r.port_robot_real   
    });

    console.log(`REGISTER → ${robotName} | Robot UDP ${r.port_robot_sim} | Twin UDP ${r.port_robot_real   }`);
});

// ------------------------------------------
// HTTP: Enviar comando a robot
app.post("/cmd/:robotName", (req, res) => {
    const robotName = req.params.robotName;
    const { cmd, data, target = "robot" } = req.body; // target = "robot" o "twin"

    if (!robots[robotName])
        return res.status(404).json({ error: "robot not found" });

    const r = robots[robotName];
    if (!r.address)
        return res.status(400).json({ error: "robot not connected yet" });

    const port = target === "twin" ? r.port_twin : r.port_robot;

    const packet = Buffer.from(JSON.stringify({
        src: "dispatcher",
        dst: robotName,
        type: "cmd",
        cmd,
        data,
        ts: Date.now()
    }));

    dispatchSock.send(packet, port, r.address, (err) => {
        if (err) console.log('Send error:', err);
    });

    console.log(`CMD → ${robotName} (${target}) ::`, { cmd, data });
    res.json({ status: "sent", target, port });
});

// ------------------------------------------
// UDP Router: recibe estado y reenvía comandos
dispatchSock.on("message", (msg, rinfo) => {
    try {
        const packet = JSON.parse(msg.toString());

        // Update origin robot address y timestamp
        if (packet.src && robots[packet.src]) {
            robots[packet.src].address = rinfo.address;
            robots[packet.src].last_ts = Date.now();
        }

        const dst = packet.dst;

        // Logs / state; store last_state for monitoring
        if (!dst || dst === "dispatcher") {
            console.log("STATE:", packet);
            if (packet.src && robots[packet.src] && packet.type === 'state') {
                robots[packet.src].last_state = packet.data || null;
            }
            return;
        }

        // Unknown robot
        if (!robots[dst]) {
            console.log(`UNKNOWN DEST: ${dst}`);
            return;
        }

        const target = robots[dst];
        const port = rinfo.port; // el robot se conecta desde su puerto
        const json = Buffer.from(JSON.stringify(packet));

        if (!target.address) {
            console.log(`ROUTE SKIPPED - ${dst} has no address yet`);
            return;
        }

        dispatchSock.send(json, target.port_robot, target.address, (err) => {
            if (err) console.log('Send error:', err);
        });

        console.log(`ROUTE ${packet.src} → ${dst}`);

    } catch (err) {
        console.log("Invalid UDP JSON:", err);
    }
});

// ------------------------------------------
// Liberar robots inactivos (5 min timeout)
setInterval(() => {
    const now = Date.now();
    for (const [name, r] of Object.entries(robots)) {
        if (r.last_ts && now - r.last_ts > 5 * 60 * 1000) { // 5 minutos
            console.log(`TIMEOUT → ${name} inactivo, liberando address`);
            r.address = null;
            r.last_state = null;
            r.last_ts = null;
        }
    }
}, 60 * 1000);

// ------------------------------------------
// Expose robots state
app.get('/robots', (req, res) => {
    const connected = {};
    for (const [k, v] of Object.entries(robots)) {
        if (v.last_state) connected[k] = v;
    }
    res.json(connected);
});

app.get('/robots/all', (req, res) => {
    res.json(robots);
});

// ------------------------------------------
// Start UDP + HTTP
dispatchSock.bind(cfg.dispatcher_udp_port, () => {
    console.log(`Dispatcher UDP running on port ${cfg.dispatcher_udp_port}`);
});

app.listen(cfg.dispatcher_http_port, () => {
    console.log(`Dispatcher HTTP listening on port ${cfg.dispatcher_http_port}`);
});
