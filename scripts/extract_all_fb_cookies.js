#!/usr/bin/env node
/**
 * 从 Windows Chrome CDP 提取全部 FB cookie（包括 datr, sb 等关键 session cookie）
 * 用法：确保 Windows Chrome 以 --remote-debugging-port=9222 启动 → node 此脚本
 * 输出：/home/user/fb_data/cookies_fresh.json
 */
const CDP = require('chrome-remote-interface');
const fs = require('fs');

(async () => {
  const client = await CDP({ host: '127.0.0.1', port: 9222 });
  const { Network, Page } = client;
  await Page.enable();
  await Network.enable();

  // Navigate to FB to get all cookies in context
  await Page.navigate({ url: 'https://www.facebook.com/' });
  await new Promise(r => Page.loadEventFired(r));
  // Wait for redirects/login state
  await new Promise(r => setTimeout(r, 6000));

  // Get all browser cookies for facebook.com
  const { cookies } = await Network.getCookies();
  const fbCookies = cookies.filter(c =>
    c.domain.includes('facebook.com') || c.domain === '.facebook.com'
  );

  console.log(`\n找到 ${fbCookies.length} 个 FB cookie:`);

  // Build cookie array for Playwright (same format fb_scraper.js uses)
  const fullCookieArray = fbCookies
    .filter(c => ['c_user', 'xs', 'fr', 'datr', 'sb', 'dpr', 'ps_l', 'ps_n', 'wd'].includes(c.name))
    .map(c => ({
      name: c.name,
      value: c.value,
      domain: c.domain || '.facebook.com',
      path: c.path || '/',
      ...(c.sameSite === 'Lax' ? { sameSite: 'Lax' } : {}),
    }));

  // Also include any other FB cookies not in the known list
  const knownNames = new Set(['c_user', 'xs', 'fr', 'datr', 'sb', 'dpr', 'ps_l', 'ps_n', 'wd']);
  const extraCookies = fbCookies
    .filter(c => !knownNames.has(c.name))
    .map(c => ({
      name: c.name,
      value: c.value,
      domain: c.domain || '.facebook.com',
      path: c.path || '/',
    }));

  fullCookieArray.push(...extraCookies);

  // Log summary
  fbCookies.forEach(c => {
    const icon = ['c_user', 'xs', 'fr', 'datr', 'sb'].includes(c.name) ? '🔑' : '  ';
    console.log(`  ${icon} ${c.name}=${c.value.substring(0, 20)}...`);
  });

  const c_user = fbCookies.find(c => c.name === 'c_user');
  const xs = fbCookies.find(c => c.name === 'xs');
  const datr = fbCookies.find(c => c.name === 'datr');

  if (!c_user || !xs) {
    console.log('\n❌ 未登录 FB！请先在打开的 Chrome 中登录 facebook.com');
    client.close();
    process.exit(1);
  }

  const output = {
    c_user: c_user.value,
    xs: xs.value,
    has_datr: !!datr,
    fullCookieArray,
    cookieCount: fullCookieArray.length,
    extracted_at: new Date().toISOString(),
  };

  const outputPath = '/home/user/fb_data/cookies_fresh.json';
  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));
  console.log(`\n✅ 已保存 ${fullCookieArray.length} 个 cookie 到 ${outputPath}`);
  console.log(`   datr: ${datr ? '✅ 有' : '❌ 无'} — 这是设备信任的关键 cookie`);

  client.close();
})().catch(e => {
  console.error('❌', e.message);
  process.exit(1);
});
