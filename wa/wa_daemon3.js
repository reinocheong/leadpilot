const { default: makeWASocket, useMultiFileAuthState } = require("@whiskeysockets/baileys");
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const SESSION_DIR = path.resolve(__dirname, 'wa_session');
const QR_TEXT_FILE = '/tmp/wa_qr.txt';
const QR_IMAGE_FILE = '/tmp/wa_qr.png';

// Do NOT clear session — preserve paired credentials
// Only clear when explicitly re-pairing

let sock = null;
let wsConnected = false;
let backoffMinutes = 0;
let reconnectTimer = null;

// HTTP server
const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  if (req.url === '/health') {
    res.end(JSON.stringify({ ok: true, pid: process.pid, connected: wsConnected, uptime: process.uptime().toFixed(0) }));
    return;
  }
  if (req.url === '/send' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { phone, message } = JSON.parse(body);
        if (!phone || !message) { res.statusCode = 400; res.end(JSON.stringify({ ok: false, error: 'missing phone or message' })); return; }
        const jid = phone.includes('@s.whatsapp.net') ? phone : `${phone.replace('+', '')}@s.whatsapp.net`;
        if (!sock) { res.end(JSON.stringify({ ok: false, error: 'WhatsApp not connected' })); return; }
        await sock.sendMessage(jid, { text: message });
        console.log(`[wa_daemon] ✅ 已发送给 ${phone}`);
        res.end(JSON.stringify({ ok: true }));
      } catch (e) {
        console.error(`[wa_daemon] ❌ 发送失败: ${e.message}`);
        res.statusCode = 500; res.end(JSON.stringify({ ok: false, error: e.message }));
      }
    });
    return;
  }
  // Fetch latest messages from a WhatsApp Channel (newsletter)
  // Usage: GET /fetch_channel?invite=0029Vb6p7Qq5Ejy68g8VCj1U
  // Or:    POST /fetch_channel with JSON body {"invite": "0029Vb6p7Qq5Ejy68g8VCj1U"}
  const channelMatch = req.url.match(/^\/fetch_channel(?:\?invite=([^&]+))?/);
  if (channelMatch && (req.method === 'GET' || req.method === 'POST')) {
    let invite = channelMatch[1] || '';
    const respond = (code, data) => { res.statusCode = code; res.end(JSON.stringify(data)); };
    if (req.method === 'POST' && !invite) {
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', async () => {
        try {
          invite = JSON.parse(body).invite || '';
          if (!invite) { respond(400, { ok: false, error: 'missing invite' }); return; }
          await doFetchChannel(invite, respond);
        } catch (e) { respond(500, { ok: false, error: e.message }); }
      });
      return;
    }
    if (!invite) { respond(400, { ok: false, error: 'missing ?invite=' }); return; }
    doFetchChannel(invite, respond);
    return;
  }

  res.statusCode = 404;
  res.end(JSON.stringify({ ok: false }));
});
server.listen(3456);
console.log('[wa_daemon] HTTP server on :3456');

async function doFetchChannel(invite, respond) {
  if (!sock) { respond(503, { ok: false, error: 'not connected' }); return; }
  let inviteCode = invite;
  const m = invite.match(/whatsapp\.com\/channel\/([a-zA-Z0-9_-]+)/);
  if (m) inviteCode = m[1];
  const meta = await sock.newsletterMetadata('invite', inviteCode);
  if (!meta || !meta.id) { respond(404, { ok: false, error: 'channel not found' }); return; }
  const jid = meta.id;
  const name = meta.name?.text || meta.name || 'Unknown';
  console.log(`[wa_daemon] 📰 Channel: ${name} (${jid})`);
  await sock.newsletterFollow(jid);
  console.log(`[wa_daemon] ✅ Followed: ${name}`);
  try { await sock.subscribeNewsletterUpdates(jid); } catch(e) {}
  respond(200, { ok: true, channel: { id: jid, name }, message: 'Subscribed. Will capture prices via live listener.' });
}

async function startSock() {
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
  sock = makeWASocket({
    auth: state,
    shouldSyncLogicMessage: () => true,
    markOnlineOnConnect: false,
    syncFullHistory: false,
    maxMsgRetryCount: 2,
    browser: ['Chrome (Linux)', '', ''],
  });

  sock.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      console.log('[wa_daemon] 📱 QR generated');
      fs.writeFileSync(QR_TEXT_FILE, qr);

      // Spawn Python to generate QR image immediately
      const py = spawn('python3', ['-c', `
import qrcode, sys
qr_str = sys.stdin.read().strip()
qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
qr.add_data(qr_str)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
img.save("/tmp/wa_qr.png")
print("QR_IMAGE_SAVED")
      `]);
      py.stdin.write(qr);
      py.stdin.end();
      py.stdout.on('data', d => console.log('[qrgen]', d.toString().trim()));
      py.stderr.on('data', d => console.error('[qrgen]', d.toString().trim()));

      wsConnected = false;
      return;
    }

    if (connection === 'open') {
      wsConnected = true;
      backoffMinutes = 0;
      console.log('[wa_daemon] ✅ CONNECTED - WhatsApp linked!（退避已重置）');
      // Write a signal file so we know it's connected
      fs.writeFileSync('/tmp/wa_connected.txt', new Date().toISOString());
    } else if (connection === 'close') {
      wsConnected = false;
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const errInfo = {
        statusCode,
        message: lastDisconnect?.error?.message,
      };
      console.log('[wa_daemon] 🔌 Disconnected:', JSON.stringify(errInfo));

      if (statusCode !== 401 && statusCode !== 403) {
        // 指数退避重连：5分 → 10分 → 20分 → 40分 → 60分（上限）
        backoffMinutes = Math.min(Math.max(backoffMinutes * 2, 5), 60);
        console.log(`[wa_daemon] ⏳ ${backoffMinutes} 分钟后重连...（防封）`);

        if (reconnectTimer) clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null;
          startSock().catch(e =>
            console.error('[wa_daemon] ❌ 重连失败:', e.message)
          );
        }, backoffMinutes * 60 * 1000);
      } else {
        console.log(`[wa_daemon] 🛑 停止重连（statusCode=${statusCode}，需手动处理）`);
        process.exit(1);
      }
    }
  });

  sock.ev.on('creds.update', saveCreds);

  // Listen for channel (newsletter) messages
  sock.ev.on('messages.upsert', ({ messages, type }) => {
    for (const msg of messages) {
      const jid = msg.key?.remoteJid || '';
      if (jid.endsWith('@newsletter')) {
        const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
        if (text) {
          console.log(`[wa_daemon] 📰 Channel msg from ${jid}: ${text.substring(0, 100)}`);
          const outDir = path.resolve(__dirname, '..', '..', 'jbkitchen', 'site', 'data');
          fs.mkdirSync(outDir, { recursive: true });
          fs.writeFileSync(path.join(outDir, 'chan_raw.json'), JSON.stringify({
            updated: new Date().toISOString(),
            jid,
            text,
            full: msg
          }, null, 2));
        }
      }
    }
  });
}

startSock().catch(e => {
  console.error('[wa_daemon] Fatal:', e.message);
  process.exit(1);
});
