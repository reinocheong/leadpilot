const { default: makeWASocket, useMultiFileAuthState } = require("@whiskeysockets/baileys");
const http = require('http');
const { handleIncomingMessage } = require('./lib/message_router');

let sock = null;  // make accessible to HTTP handler
let wsConnected = false;  // track WebSocket connection state

async function startSock() {
  const { state, saveCreds, saveState } = await useMultiFileAuthState('wa_session');
  sock = makeWASocket({
    auth: state,
    printQRInTerminal: true,
    // Auto-reconnect on disconnect
    shouldSyncLogicMessage: () => true,
    markOnlineOnConnect: true,
  });

  // ── Connection state tracking + auto-reconnect ──
  sock.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      console.log('[wa_daemon] 📱 QR code received — needs re-auth');
      wsConnected = false;
      return;
    }

    if (connection === 'open') {
      wsConnected = true;
      console.log('[wa_daemon] 🔗 WhatsApp 已连接');
    } else if (connection === 'close') {
      wsConnected = false;
      const shouldReconnect =
        lastDisconnect?.error?.output?.statusCode !== 401;  // 401 = logout, don't reconnect
      console.log(
        `[wa_daemon] 🔌 连接断开${shouldReconnect ? '，5 秒后重连...' : '（需重新扫码）'}`
      );
      if (shouldReconnect) {
        setTimeout(() => startSock().catch(e =>
          console.error('[wa_daemon] ❌ 重连失败:', e.message)
        ), 5000);
      }
    }
  });

  sock.ev.on('creds.update', saveCreds);
  sock.ev.on('messages.upsert', m => handleIncomingMessage(sock, m));

  http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');

    // ── /health ──
    if (req.url === '/health') {
      res.end(JSON.stringify({
        ok: true,
        pid: process.pid,
        connected: wsConnected,
        uptime: process.uptime().toFixed(0),
      }));
      return;
    }

    // ── /send (POST) ──
    if (req.url.startsWith('/send') && req.method === 'POST') {
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', async () => {
        try {
          const { phone, message } = JSON.parse(body);
          if (!phone || !message) {
            res.statusCode = 400;
            res.end(JSON.stringify({ ok: false, error: 'missing phone or message' }));
            return;
          }

          // Format: 60123456789@s.whatsapp.net
          const jid = phone.includes('@s.whatsapp.net')
            ? phone
            : `${phone.replace('+', '')}@s.whatsapp.net`;

          if (!sock) {
            res.end(JSON.stringify({ ok: false, error: 'WhatsApp not connected' }));
            return;
          }

          await sock.sendMessage(jid, { text: message });
          console.log(`[wa_daemon] ✅ 已发送给 ${phone}`);
          res.end(JSON.stringify({ ok: true, queued: false }));
        } catch (e) {
          console.error(`[wa_daemon] ❌ 发送失败: ${e.message}`);
          res.statusCode = 500;
          res.end(JSON.stringify({ ok: false, error: e.message }));
        }
      });
      return;
    }

    // ── fallback ──
    res.statusCode = 404;
    res.end(JSON.stringify({ ok: false, error: 'not found' }));

  }).listen(3456);

  console.log('[wa/wa_daemon.js] 服务运行在 3456');
}

startSock();
