const { default: makeWASocket, useMultiFileAuthState } = require("@whiskeysockets/baileys");
const fs = require('fs');
const path = require('path');

const SESSION_DIR = path.resolve(__dirname, 'wa_session');
const QR_FILE = '/tmp/wa_live_qr.txt';

async function start() {
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
  const sock = makeWASocket({
    auth: state,
    shouldSyncLogicMessage: () => true,
    markOnlineOnConnect: false,
    syncFullHistory: false,
    maxMsgRetryCount: 2,
    browser: ['Chrome (Linux)', '', ''],
  });

  sock.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      fs.writeFileSync(QR_FILE, qr);
      process.stdout.write('QR_READY\n');
      return;
    }
    if (connection === 'open') {
      process.stdout.write('CONNECTED\n');
    } else if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode;
      if (code === 401 || code === 403) {
        process.stdout.write('FATAL:' + code + '\n');
        process.exit(1);
      }
    }
  });

  sock.ev.on('creds.update', saveCreds);

  // HTTP server (health + send)
  const http = require('http');
  const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    if (req.url === '/health') {
      const connected = fs.existsSync(SESSION_DIR + '/creds.json');
      res.end(JSON.stringify({ ok: true, pid: process.pid, connected }));
      return;
    }
    res.statusCode = 404;
    res.end(JSON.stringify({ ok: false }));
  });
  server.listen(3456);
  process.stdout.write('HTTP_READY:3456\n');
}

start().catch(e => process.exit(1));
