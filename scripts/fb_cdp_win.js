#!/usr/bin/env node
/**
 * FB 发帖 — 通过 Windows Chrome CDP
 * 步骤：首页 → 点击"分享你的新鲜事" → 弹窗 → 输入 → 发布
 */
const CDP = require('chrome-remote-interface');
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

(async () => {
  let msg = process.env.FB_POST_MSG;
  if (!msg) { 
    // Try reading from a file
    const filePath = process.argv[2];
    if (filePath) {
      const fs = require('fs');
      msg = fs.readFileSync(filePath, 'utf8').trim();
    }
  }
  if (!msg) { console.error('❌ 请设置 FB_POST_MSG 或传入文件路径'); process.exit(1); }
  console.log(`[fb] 内容: ${msg.substring(0,50)}... (${msg.length}字)`);

  const client = await CDP({ host: '127.0.0.1', port: 9222 });
  const { Page, Runtime, Input } = client;
  await Page.enable(); await Runtime.enable();

  // 1. 首页
  console.log('[fb] 打开首页...');
  await Page.navigate({ url: 'https://www.facebook.com/' });
  await new Promise(r => { Page.loadEventFired(r); });
  await sleep(6000);

  // 2. 点击发帖框
  console.log('[fb] 点击发帖框...');
  await Runtime.evaluate({
    expression: `(function(){
      // Find the composer button by text or aria-label
      const btns = [...document.querySelectorAll('[role="button"]')];
      const target = btns.find(b => {
        const t = (b.textContent||'').trim();
        const a = (b.getAttribute('aria-label')||'');
        return t.includes('分享你的新鲜事') || a.includes('分享你的新鲜事') || a.includes('发')&&a.includes('个人主页');
      }) || btns.find(b => b.getAttribute('aria-label')?.includes('发布到'));
      if (target) { target.click(); return 'clicked'; }
      return 'not found';
    })()`,
  });
  await sleep(4000);

  // 3. 输入内容
  console.log('[fb] 输入内容...');
  // Focus the contenteditable in the dialog
  await Runtime.evaluate({ expression: `document.querySelector('[role="dialog"] [contenteditable="true"]')?.focus()` });
  await sleep(500);

  for (const char of msg) {
    if (char === '\n') {
      await Input.dispatchKeyEvent({ type: 'keyDown', key: 'Enter', windowsVirtualKeyCode: 13 });
      await Input.dispatchKeyEvent({ type: 'keyUp', key: 'Enter', windowsVirtualKeyCode: 13 });
    } else {
      await Input.dispatchKeyEvent({ type: 'char', text: char, unmodifiedText: char, key: char, windowsVirtualKeyCode: char.charCodeAt(0) });
    }
    await sleep(10);
  }
  await sleep(1500);

  // 4. 点击发布
  console.log('[fb] 发布...');
  const result = await Runtime.evaluate({
    expression: `(function(){
      const btns = [...document.querySelectorAll('[role="dialog"] [role="button"], [role="button"]')].filter(b => b.offsetHeight>0);
      for (const b of btns) {
        const t = (b.textContent||'').trim();
        const a = (b.getAttribute('aria-label')||'').toLowerCase();
        if ((t==='发帖'||t==='发布'||t==='Post'||a==='发布'||a==='post'||a==='发帖') && !b.disabled && !b.hasAttribute('aria-disabled')) {
          b.click();
          return 'posted';
        }
      }
      return 'not found: ' + btns.map(b=>'['+(b.textContent||'').trim().substring(0,20)+']').filter(t=>t!=='[]').slice(0,15).join(' ');
    })()`,
  });
  const r = result?.result?.value || 'unknown';
  console.log('[fb] 结果:', r);

  // 5. 等发布完成
  await sleep(4000);
  console.log('[fb] ✅', r === 'posted' ? '发布成功！' : '需要检查');
  
  // Check dialog closed
  const dialog = await Runtime.evaluate({ expression: `document.querySelector('[role="dialog"]') !== null` });
  console.log('[fb] 对话框状态:', dialog.result.value ? '还在' : '已关闭');
  
  client.close();
  process.exit(r === 'posted' ? 0 : 1);
})().catch(e => { console.error('❌', e.message); process.exit(1); });
