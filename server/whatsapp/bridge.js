/**
 * Dione AI — WhatsApp Web Bridge
 */

import { default as makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, makeCacheableSignalKeyStore } from "@whiskeysockets/baileys";
import { createServer } from "node:http";
import { mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import QRCode from "qrcode";
import pino from "pino";

const DIONE_PORT   = parseInt(process.env.DIONE_PORT   || "8900", 10);
const BRIDGE_PORT  = parseInt(process.env.BRIDGE_PORT  || "8901", 10);
const AUTH_DIR     = process.env.WA_AUTH_DIR || path.join(
  path.dirname(fileURLToPath(import.meta.url)), "..", "..", "data", "whatsapp_auth"
);

const DIONE_INBOUND_URL = `http://127.0.0.1:${DIONE_PORT}/api/channels/whatsapp/inbound`;
const logger = pino({ level: process.env.LOG_LEVEL || "warn" });
const REPLY_SCOPE = (process.env.WA_REPLY_SCOPE || "personal").toLowerCase();
const ALLOWED_CHAT_ID = (process.env.WA_ALLOWED_CHAT_ID || "").trim();
const ALLOWED_NUMBER = (process.env.WA_ALLOWED_NUMBER || "").replace("+", "").trim();

let sock = null;
let currentQR = null;
let currentQRDataUrl = null;
let currentQRTerminal = null;
let connectionStatus = "disconnected";
let reconnectAttempts = 0;
const MAX_RECONNECT = 10;
const RECONNECT_BASE_MS = 2000;

function normalizeJidNumber(jid = "") {
  return String(jid)
    .split(":")[0]
    .replace("@s.whatsapp.net", "")
    .replace("@lid", "")
    .trim();
}

function isSelfChat(senderJid = "") {
  const selfNumber = normalizeJidNumber(sock?.user?.id || "");
  const chatNumber = normalizeJidNumber(senderJid);
  return !!selfNumber && selfNumber === chatNumber;
}

function shouldProcessForReply(senderJid, isGroup) {
  if (REPLY_SCOPE === "all") return true;

  // Default "personal": only self chat (not groups/broadcast)
  const isDirectJid = senderJid.endsWith("@s.whatsapp.net") || senderJid.endsWith("@lid");
  if (isGroup || !isDirectJid) return false;

  if (ALLOWED_CHAT_ID) {
    return senderJid === ALLOWED_CHAT_ID;
  }

  if (ALLOWED_NUMBER) {
    const chatNumber = normalizeJidNumber(senderJid);
    return chatNumber === ALLOWED_NUMBER;
  }

  return isSelfChat(senderJid);
}

async function connectWhatsApp() {
  await mkdir(AUTH_DIR, { recursive: true });

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  connectionStatus = "connecting";
  currentQR = null;
  currentQRDataUrl = null;
  currentQRTerminal = null;

  sock = makeWASocket({
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    version,
    browser: ["Dione AI", "Desktop", "1.0.0"],
    printQRInTerminal: false,
    syncFullHistory: false,
    markOnlineOnConnect: false,
    logger,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      currentQR = qr;
      connectionStatus = "qr";
      try {
        currentQRDataUrl = await QRCode.toDataURL(qr, { width: 300, margin: 2 });
      } catch {}
      try {
        currentQRTerminal = await QRCode.toString(qr, { type: "utf8", small: true });
      } catch {}
      console.log("[whatsapp-bridge] QR code ready — scan with your WhatsApp app");
    }

    if (connection === "open") {
      connectionStatus = "connected";
      currentQR = null;
      currentQRDataUrl = null;
      currentQRTerminal = null;
      reconnectAttempts = 0;
      const me = sock.user;
      console.log(`[whatsapp-bridge] Connected as ${me?.id || "unknown"}`);
    }

    if (connection === "close") {
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;

      if (loggedOut) {
        connectionStatus = "disconnected";
        console.log("[whatsapp-bridge] Logged out — session cleared");
        try { await rm(AUTH_DIR, { recursive: true, force: true }); } catch {}
        return;
      }

      reconnectAttempts++;
      if (reconnectAttempts > MAX_RECONNECT) {
        connectionStatus = "disconnected";
        console.error("[whatsapp-bridge] Max reconnect attempts reached");
        return;
      }

      const delay = Math.min(RECONNECT_BASE_MS * Math.pow(1.5, reconnectAttempts - 1), 30000);
      console.log(`[whatsapp-bridge] Reconnecting in ${Math.round(delay / 1000)}s (attempt ${reconnectAttempts}/${MAX_RECONNECT})`);
      connectionStatus = "connecting";
      setTimeout(connectWhatsApp, delay);
    }
  });

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (!["notify", "append"].includes(type)) return;

    for (const msg of messages) {
      if (msg.key.remoteJid === "status@broadcast") continue;

      const text = msg.message?.conversation
        || msg.message?.extendedTextMessage?.text
        || msg.message?.imageMessage?.caption
        || msg.message?.videoMessage?.caption
        || "";

      if (!text.trim()) continue;

      const senderJid = msg.key.remoteJid || "";
      const senderName = msg.pushName || "";
      const isGroup = senderJid.endsWith("@g.us");
      const participantJid = isGroup ? (msg.key.participant || "") : senderJid;

      // Ignore device-originated outbound messages except self-chat commands.
      if (msg.key.fromMe && !isSelfChat(senderJid)) {
        continue;
      }

      if (!shouldProcessForReply(senderJid, isGroup)) {
        continue;
      }

      try {
        const payload = {
          text: text.trim(),
          sender_id: participantJid.replace("@s.whatsapp.net", "").replace("@lid", ""),
          sender_name: senderName,
          chat_id: senderJid,
          is_group: isGroup,
          message_id: msg.key.id || "",
        };

        const resp = await fetch(DIONE_INBOUND_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (resp.ok) {
          const data = await resp.json();
          if (data.reply) {
            await sock.readMessages([msg.key]);
            await sock.sendPresenceUpdate("composing", senderJid);
            await new Promise(r => setTimeout(r, 500));
            await sock.sendPresenceUpdate("paused", senderJid);
            await sock.sendMessage(senderJid, { text: data.reply });
          }
        }
      } catch (err) {
        console.error("[whatsapp-bridge] Failed to forward message:", err.message);
      }
    }
  });
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", c => data += c);
    req.on("end", () => {
      try { resolve(JSON.parse(data)); }
      catch { resolve({}); }
    });
    req.on("error", reject);
  });
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${BRIDGE_PORT}`);
  res.setHeader("Content-Type", "application/json");

  if (req.method === "GET" && url.pathname === "/status") {
    const me = sock?.user;
    res.end(JSON.stringify({
      status: connectionStatus,
      user: me ? { id: me.id, name: me.name } : null,
      reconnectAttempts,
      hasQR: !!currentQR,
    }));
    return;
  }

  if (req.method === "GET" && url.pathname === "/qr") {
    if (currentQRDataUrl) {
      res.end(JSON.stringify({ qr: currentQRDataUrl, terminal: currentQRTerminal, status: connectionStatus }));
    } else if (connectionStatus === "connected") {
      res.end(JSON.stringify({ qr: null, terminal: null, status: "connected", message: "Already connected" }));
    } else {
      res.end(JSON.stringify({ qr: null, terminal: null, status: connectionStatus, message: "No QR available yet" }));
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/send") {
    if (connectionStatus !== "connected" || !sock) {
      res.statusCode = 503;
      res.end(JSON.stringify({ error: "WhatsApp not connected" }));
      return;
    }

    const body = await parseBody(req);
    const { to, text, chat_id } = body;
    const jid = chat_id || (to ? `${to.replace("+", "")}@s.whatsapp.net` : "");

    if (!jid || !text) {
      res.statusCode = 400;
      res.end(JSON.stringify({ error: "Missing 'to'/'chat_id' and 'text'" }));
      return;
    }

    try {
      await sock.sendPresenceUpdate("composing", jid);
      await new Promise(r => setTimeout(r, 300));
      const result = await sock.sendMessage(jid, { text });
      await sock.sendPresenceUpdate("paused", jid);
      res.end(JSON.stringify({ ok: true, messageId: result?.key?.id }));
    } catch (err) {
      res.statusCode = 500;
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/logout") {
    try {
      if (sock) await sock.logout();
    } catch {}
    try { await rm(AUTH_DIR, { recursive: true, force: true }); } catch {}
    connectionStatus = "disconnected";
    currentQR = null;
    currentQRDataUrl = null;
    currentQRTerminal = null;
    res.end(JSON.stringify({ ok: true, message: "Logged out" }));
    setTimeout(connectWhatsApp, 1000);
    return;
  }

  if (req.method === "POST" && url.pathname === "/restart") {
    reconnectAttempts = 0;
    if (sock) {
      try { sock.end(undefined); } catch {}
    }
    setTimeout(connectWhatsApp, 500);
    res.end(JSON.stringify({ ok: true, message: "Restarting" }));
    return;
  }

  res.statusCode = 404;
  res.end(JSON.stringify({ error: "Not found" }));
});

server.listen(BRIDGE_PORT, "127.0.0.1", () => {
  console.log(`[whatsapp-bridge] HTTP API listening on http://127.0.0.1:${BRIDGE_PORT}`);
  console.log(`[whatsapp-bridge] Forwarding messages to ${DIONE_INBOUND_URL}`);
  connectWhatsApp();
});

process.on("SIGINT", () => {
  console.log("[whatsapp-bridge] Shutting down...");
  if (sock) try { sock.end(undefined); } catch {}
  server.close();
  process.exit(0);
});

process.on("SIGTERM", () => {
  if (sock) try { sock.end(undefined); } catch {}
  server.close();
  process.exit(0);
});
