#!/usr/bin/env node
/**
 * 通过 Windows Chrome CDP 发帖到 FB timeline
 * 用法: node scripts/fb_cdp_post.js
 * 消息内容通过环境变量 FB_POST_MSG 传入，或使用默认测试消息
 */
const CDP = require('chrome-remote-interface');
const fs = require('fs');

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

(async () => {
  const message = process.env.FB_POST_MSG || fs.readFileSync('/dev/stdin', 'utf8').trim();
  // Also support file argument
  const msgFile = process.argv[2];
  const msg = msgFile ? fs.readFileSync(msgFile, 'utf8').trim() : message;
  
  if (!msg || msg.length < 5) {
    console.error('用法: FB_POST_MSG="内容" node scripts/fb_cdp_post.js');
    console.error('  或: node scripts/fb_cdp_post.js < message.txt');
    process.exit(1);
  }

  console.log(`[cdp] 内容: ${msg.substring(0, 50)}... (${msg.length}字)`);
  console.log('[cdp] 连接 Chrome...');
  
  const client = await CDP({ host: '127.0.0.1', port: 9222 });
  const { Page, Runtime } = client;
  await Page.enable();
  await Runtime.enable();
  
  // Navigate to FB
  console.log('[cdp] 打开 FB...');
  await Page.navigate({ url: 'https://www.facebook.com/me' });
  await new Promise(resolve => {
    Page.loadEventFired(() => {
      console.log('[cdp] 页面加载完成');
      resolve();
    });
  });
  await sleep(5000);

  // Click composer
  console.log('[cdp] 点击发帖按钮...');
  const clickResult = await Runtime.evaluate({
    expression: `document.querySelector('div[role="button"][aria-label*="个人主页"]')?.click() || 
                 [...document.querySelectorAll('[role="button"]')].find(b => {
                   const t = (b.textContent||'').toLowerCase();
                   const a = (b.getAttribute('aria-label')||'').toLowerCase();
                   return (t.includes('post') || a.includes('post') || t.includes('发') || a.includes('发'));
                 })?.click(); 'clicked'`,
    awaitPromise: false,
  });
  console.log('[cdp] 已点击');
  await sleep(4000);

  // Type message using the keyboard
  console.log('[cdp] 输入内容...');
  const { Input } = client;
  await Input.dispatchKeyEvent({ type: 'keyDown', key: 'Tab' });
  await Input.dispatchKeyEvent({ type: 'keyUp', key: 'Tab' });
  await sleep(200);

  // Type the message character by character via Input
  for (const char of msg) {
    if (char === '\n') {
      await Input.dispatchKeyEvent({ type: 'keyDown', key: 'Enter', windowsVirtualKeyCode: 13 });
      await Input.dispatchKeyEvent({ type: 'keyUp', key: 'Enter', windowsVirtualKeyCode: 13 });
    } else {
      await Input.dispatchKeyEvent({
        type: 'char',
        text: char,
        unmodifiedText: char,
        key: char,
        windowsVirtualKeyCode: char.charCodeAt(0),
      });
    }
    await sleep(30);
  }
  console.log('[cdp] 输入完成');
  await sleep(1500);

  // Click Post button
  console.log('[cdp] 查找发布按钮...');
  const postResult = await Runtime.evaluate({
    expression: `(function(){
      const all = [...document.querySelectorAll('div[role="button"]')].filter(b => b.offsetHeight > 0);
      for (const b of all) {
        const t = (b.textContent||'').trim();
        const a = (b.getAttribute('aria-label')||'').toLowerCase();
        if (t === '发布' || t === 'Post' || a === '发布' || a === 'post') {
          if (!b.disabled && !b.hasAttribute('aria-disabled')) {
            b.click();
            return 'posted: ' + (a || t);
          }
        }
      }
      return 'not found';
    })()`,
  });
  console.log('[cdp]', postResult?.result?.value || 'unknown');

  await sleep(3000);
  console.log('[cdp] ✅ 完成');
  client.close();
  process.exit(0);
})().catch(e => {
  console.error('[cdp] ❌ 失败:', e.message);
  process.exit(1);
});
