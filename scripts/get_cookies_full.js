const { chromium } = require('playwright');

(async () => {
  try {
    console.log('Connecting to Chrome via CDP on localhost:9222...');
    const browser = await chromium.connectOverCDP('http://localhost:9222');
    console.log('Connected!');

    const contexts = browser.contexts();
    const defaultContext = contexts[0] || await browser.newContext();
    let page = defaultContext.pages()[0] || await defaultContext.newPage();

    console.log('Navigating to Facebook...');
    await page.goto('https://www.facebook.com', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    const allCookies = await defaultContext.cookies();
    const fbCookies = allCookies.filter(c => c.domain.includes('facebook.com') || c.domain.includes('.facebook.com'));

    console.log(`\n=== FB COOKIES (${fbCookies.length} total) ===`);

    // Build full cookie array — all domains, all names
    const fullCookieArray = fbCookies.map(c => ({
      name: c.name,
      value: c.value,
      domain: c.domain || '.facebook.com',
      path: c.path || '/',
      ...(c.sameSite ? { sameSite: c.sameSite } : {}),
    }));

    fbCookies.forEach(c => {
      const icon = ['c_user', 'xs', 'fr', 'datr', 'sb'].includes(c.name) ? '🔑' : '  ';
      console.log(`  ${icon} ${c.name}=${c.value.substring(0, 25)}...`);
    });

    const c_user = fbCookies.find(c => c.name === 'c_user');
    const xs = fbCookies.find(c => c.name === 'xs');
    const datr = fbCookies.find(c => c.name === 'datr');

    if (c_user && xs) {
      const fs = require('fs');
      // Save WSL path (for Hermes scraper)
      const wslOutput = '/home/user/fb_data/cookies_fresh.json';
      const windowsOutput = 'C:\\Users\\User\\Desktop\\fb-cookie-extract\\cookies_fresh.json';

      const output = {
        c_user: c_user.value,
        xs: xs.value,
        has_datr: !!datr,
        fullCookieArray,
        cookieCount: fullCookieArray.length,
        extracted_at: new Date().toISOString(),
      };

      fs.writeFileSync(wslOutput, JSON.stringify(output, null, 2));
      fs.writeFileSync(windowsOutput, JSON.stringify(output, null, 2));

      console.log(`\n✅ 共 ${fullCookieArray.length} 个 cookie`);
      console.log(`✅ datr: ${datr ? '存在 ✓ (设备信任关键)' : '缺失'}`);
      console.log(`✅ 已保存到: ${wslOutput}`);
    } else {
      console.log('\n❌ c_user 或 xs 未找到 — 是否已登录 Facebook？');
    }

    console.log('\nDone.');
  } catch (err) {
    console.error('ERROR:', err.message);
    process.exit(1);
  }
})();
