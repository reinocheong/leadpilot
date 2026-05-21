#!/usr/bin/env node
/**
 * Smart Tenancy Pro — WhatsApp Notify CLI
 * Thin client that talks to wa_daemon.js via HTTP.
 * 
 * Usage:
 *   node wa_notify.js send <phone> <message>
 * 
 * Requires wa_daemon.js running on localhost:3456
 */

const http = require('http');

function send(phone, message) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify({ phone, message });
        const req = http.request({
            hostname: '127.0.0.1',
            port: 3456,
            path: '/send',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(data)
            },
            timeout: 10000
        }, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    const result = JSON.parse(body);
                    if (result.ok) {
                        if (result.queued) {
                            console.log(`⏳ 消息已排队 (WhatsApp 未连接，连接后自动发送)`);
                        }
                        resolve(result);
                    } else {
                        reject(new Error(result.error || 'Unknown error'));
                    }
                } catch(e) {
                    reject(new Error(`Invalid response: ${body}`));
                }
            });
        });
        
        req.on('error', (e) => {
            reject(new Error(`Daemon 未运行: ${e.message}\n请先启动: node wa_daemon.js`));
        });
        
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('请求超时，Daemon 可能未响应'));
        });
        
        req.write(data);
        req.end();
    });
}

const cmd = process.argv[2];
if (cmd === 'send') {
    const phone = process.argv[3];
    const message = process.argv.slice(4).join(' ');
    
    if (!phone || !message) {
        console.error('用法: node wa_notify.js send <phone> <message>');
        process.exit(1);
    }
    
    send(phone, message).then(result => {
        if (!result.queued) console.log(`✅ 已发送给 ${phone}`);
        process.exit(0);
    }).catch(err => {
        console.error(`❌ ${err.message}`);
        process.exit(1);
    });
} else if (cmd === 'login') {
    console.log('请直接启动 daemon: node wa_daemon.js');
    console.log('首次启动会自动生成 QR 码供扫码。');
} else {
    console.log('用法: node wa_notify.js send <phone> <message>');
    console.log('       node wa_daemon.js           (启动后台服务)');
}
