/**
 * Dione AI — WhatsApp Web Bridge
 */

import { default as makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, makeCacheableSignalKeyStore } from "@whiskeysockets/baileys";
import { createServer } from "node:http";
import { mkdir, rm, readFile } from "node:fs/promises";
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
const selfIdentifiers = new Set();
const MAX_RECONNECT = 10;
const RECONNECT_BASE_MS = 2000;

const EXT_MIME_MAP = {
  ".txt": "text/plain",
  ".pdf": "application/pdf",
  ".csv": "text/csv",
  ".json": "application/json",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".mp4": "video/mp4",
  ".mov": "video/quicktime",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".zip": "application/zip",
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

function guessMimeType(filePath = "", explicitMime = "") {
  if (explicitMime) return explicitMime;
  const ext = path.extname(filePath || "").toLowerCase();
  return EXT_MIME_MAP[ext] || "application/octet-stream";
}

function buildMediaPayload(fileBuffer, filePath, mimeType, caption = "") {
  const finalMime = guessMimeType(filePath, mimeType);
  const fileName = path.basename(filePath || "attachment");

  if (finalMime.startsWith("image/")) {
    return { image: fileBuffer, caption };
  }
  if (finalMime.startsWith("video/")) {
    return { video: fileBuffer, caption };
  }
  if (finalMime.startsWith("audio/")) {
    return { audio: fileBuffer, mimetype: finalMime, ptt: false };
  }

  return {
    document: fileBuffer,
    mimetype: finalMime,
    fileName,
    caption,
  };
}

function normalizeJidNumber(jid = "") {
  return String(jid)
    .split(":")[0]
    .replace("@s.whatsapp.net", "")
    .replace("@lid", "")
    .trim();
}

function addSelfIdentifier(jid = "") {
  const normalized = normalizeJidNumber(jid);
  if (normalized) selfIdentifiers.add(normalized);
}

function refreshSelfIdentifiersFromUser(me = null) {
  if (!me) return;
  addSelfIdentifier(me.id || "");
  addSelfIdentifier(me.lid || "");
}

function isSelfChat(senderJid = "") {
  const chatNumber = normalizeJidNumber(senderJid);
  if (!chatNumber) return false;

  // Refresh from live socket user when available
  refreshSelfIdentifiersFromUser(sock?.user || null);

  return selfIdentifiers.has(chatNumber);
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

  // Prime self identifiers from persisted auth state (includes LID for account)
  refreshSelfIdentifiersFromUser(state?.creds?.me || null);

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
      refreshSelfIdentifiersFromUser(me || null);
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
    console.log(`[whatsapp-bridge] upsert type=${type} count=${Array.isArray(messages) ? messages.length : 0}`);

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
        console.log(`[whatsapp-bridge] skip fromMe non-self chat=${senderJid}`);
        continue;
      }

      if (!shouldProcessForReply(senderJid, isGroup)) {
        console.log(`[whatsapp-bridge] skip policy chat=${senderJid} group=${isGroup}`);
        continue;
      }

      console.log(`[whatsapp-bridge] inbound accepted chat=${senderJid} fromMe=${!!msg.key.fromMe} textLen=${text.trim().length}`);

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

        console.log(`[whatsapp-bridge] forwarded to dione status=${resp.status}`);

        if (resp.ok) {
          const data = await resp.json();
          console.log(`[whatsapp-bridge] dione reply present=${Boolean(data.reply)}`);
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
    const { to, text, chat_id, file_path, caption, mime_type } = body;
    const jid = chat_id || (to ? `${to.replace("+", "")}@s.whatsapp.net` : "");

    if (!jid || (!text && !file_path)) {
      res.statusCode = 400;
      res.end(JSON.stringify({ error: "Missing 'to'/'chat_id' and either 'text' or 'file_path'" }));
      return;
    }

    try {
      await sock.sendPresenceUpdate("composing", jid);
      await new Promise(r => setTimeout(r, 300));

      let result;
      if (file_path) {
        const absPath = path.isAbsolute(file_path)
          ? file_path
          : path.resolve(process.cwd(), file_path);
        const fileBuffer = await readFile(absPath);
        const payload = buildMediaPayload(
          fileBuffer,
          absPath,
          String(mime_type || "").trim(),
          String(caption || text || "").trim(),
        );
        result = await sock.sendMessage(jid, payload);
      } else {
        result = await sock.sendMessage(jid, { text });
      }

      await sock.sendPresenceUpdate("paused", jid);
      res.end(JSON.stringify({ ok: true, messageId: result?.key?.id, hasFile: Boolean(file_path) }));
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
