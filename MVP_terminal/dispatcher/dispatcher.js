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
// ------------------------------------------
const UDP_BASE = cfg.udp_base || 10010;
let nextPort = UDP_BASE;

const robots = {}; // { robotName: { port, address, last_state, last_ts } }

const dispatchSock = dgram.createSocket("udp4");

// ------------------------------------------
// HTTP: Registrar robot y asignar puerto UDP
// ------------------------------------------
app.post("/register", (req, res) => {
    const { robot } = req.body;
    if (!robot) return res.status(400).json({ error: "robot missing" });

    const assignedPort = nextPort++;

    robots[robot] = {
        port: assignedPort,
        address: null,
        last_state: null,
        last_ts: null
    };

    console.log(`REGISTERED → ${robot} | UDP ${assignedPort}`);

    res.json({
        robot,
        udp_port: assignedPort
    });
});

// Expose current robot registry + last known state
// By default `/robots` returns only connected robots (have `last_state`).
// Use `/robots/all` to get the full registry including registered-but-not-connected.
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
// HTTP: Enviar comando a robot
// ------------------------------------------
app.post("/cmd/:robot", (req, res) => {
    const robot = req.params.robot;
    const { cmd, data } = req.body;

    if (!robots[robot])
        return res.status(404).json({ error: "robot not found" });

    const r = robots[robot];

    if (!r.address)
        return res.status(400).json({ error: "robot not connected yet" });

    const packet = Buffer.from(JSON.stringify({
        src: "dispatcher",
        dst: robot,
        type: "cmd",
        cmd,
        data,
        ts: Date.now()
    }));

    dispatchSock.send(packet, r.port, r.address);

    console.log(`CMD → ${robot} ::`, { cmd, data });

    res.json({ status: "sent" });
});

// ------------------------------------------
// UDP Router: recibe estado y reenvía comandos
// ------------------------------------------
dispatchSock.on("message", (msg, rinfo) => {
    try {
        const packet = JSON.parse(msg.toString());

        // Update origin robot address
        if (packet.src && robots[packet.src]) {
            robots[packet.src].address = rinfo.address;
        }

        const dst = packet.dst;

        // Logs / state; store last_state for monitoring
        if (!dst || dst === "dispatcher") {
            console.log("STATE:", packet);
            if (packet.src && robots[packet.src] && packet.type === 'state') {
                robots[packet.src].last_state = packet.data || null;
                robots[packet.src].last_ts = packet.ts || Date.now();
            }
            return;
        }

        // Unknown robot
        if (!robots[dst]) {
            console.log(`UNKNOWN DEST: ${dst}`);
            return;
        }

        const target = robots[dst];
        const json = Buffer.from(JSON.stringify(packet));

        if (!target.address) {
            console.log(`ROUTE SKIPPED - ${dst} has no address yet`);
            return;
        }

        dispatchSock.send(json, target.port, target.address, (err) => {
            if (err) console.log('Send error:', err);
        });

        console.log(`ROUTE ${packet.src} → ${dst}`);

    } catch (err) {
        console.log("Invalid UDP JSON:", err);
    }
});

// ------------------------------------------
// Start UDP + HTTP
// ------------------------------------------
dispatchSock.bind(cfg.dispatcher_udp_port, () => {
    console.log(`Dispatcher UDP running on port ${cfg.dispatcher_udp_port}`);
});

app.listen(cfg.dispatcher_http_port, () => {
    console.log(`Dispatcher HTTP listening on port ${cfg.dispatcher_http_port}`);
});
