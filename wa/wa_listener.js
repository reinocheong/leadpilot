#!/usr/bin/env node
/**
 * Smart Tenancy Pro — WhatsApp Listener (Baileys)
 * 监听顾客回复，自动提取 @lid 并匹配数据库
 * 
 * 用法: node wa_listener.js
 * 后台常驻运行，收到消息时：
 * 1. 提取发送者的真实 @lid
 * 2. 从消息中找指纹（Ref: xxx）
 * 3. 调用 Python 更新顾客的 wa_lid
 */

const { makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const { exec } = require('child_process');
const path = require('path');

const SESSION_DIR = path.join(__dirname, 'wa_session');
const SUB_MGR = path.join(__dirname, 'sub_mgr.py');

// Fingerprint pattern: Ref: trial-xxx or Ref: sub-xxx
const FINGERPRINT_RE = /Ref:\s*(trial|sub)-(\S+)/i;

function updateLid(lid, fingerprint) {
    return new Promise((resolve) => {
        const cmd = `python3 "${SUB_MGR}" update-lid "${lid}" "${fingerprint}"`;
        exec(cmd, (err, stdout) => {
            if (err) {
                console.log(`  ⚠️ update-lid 失败: ${err.message}`);
            } else {
                console.log(`  ✅ @lid 已更新: ${lid} → ${fingerprint}`);
                console.log(`  ${stdout.trim()}`);
            }
            resolve();
        });
    });
}

async function start() {
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            // Save QR to file for Python to convert to image
            const fs = require('fs');
            fs.writeFileSync('/tmp/wa_qr.txt', qr);
            console.log('QR_READY:' + qr.substring(0, 20) + '...');
            qrcode.generate(qr, { small: true });
            console.log('📱 QR 码已生成，请扫描登录 WhatsApp');
        }
        if (connection === 'open') {
            console.log('✅ WhatsApp 监听已启动！');
            console.log('   等待顾客回复以捕获 @lid...\n');
        }
        if (connection === 'close') {
            const code = lastDisconnect?.error?.output?.statusCode;
            if (code !== DisconnectReason.loggedOut) {
                console.log('⚠️ 断开，5 秒后重连...');
                setTimeout(start, 5000);
            } else {
                console.log('❌ 已登出，请删除 wa_session/ 重新启动');
            }
        }
    });

    // 监听新消息
    sock.ev.on('messages.upsert', async (m) => {
        const msg = m.messages[0];
        if (!msg || !msg.message || m.type !== 'notify') return;
        
        // 只处理文本消息
        const text = msg.message.conversation || msg.message.extendedTextMessage?.text;
        if (!text) return;
        
        // 发送者的真实 @lid
        const senderLid = msg.key.remoteJid;
        // 排除自己发的消息
        if (msg.key.fromMe) return;
        
        console.log(`📩 收到消息`);
        console.log(`   来自: ${senderLid}`);
        console.log(`   内容: ${text.substring(0, 80)}`);
        
        // 尝试从消息中提取指纹
        const match = text.match(FINGERPRINT_RE);
        if (match) {
            const fingerprint = match[0];  // "Ref: trial-xxx"
            console.log(`   🔍 发现指纹: ${fingerprint}`);
            await updateLid(senderLid, fingerprint);
        } else {
            // 没有指纹 — 可能顾客直接发了消息
            // 通过 @lid 查数据库（如果之前已关联）
            console.log(`   ℹ️ 无指纹，已忽略`);
        }
    });

    sock.ev.on('creds.update', saveCreds);
}

console.log('🤖 Smart Tenancy Pro — WhatsApp Listener');
start();
