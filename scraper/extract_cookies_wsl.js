// Alternative: extract cookies using local Playwright Chromium
const { chromium } = require('playwright');

(async () => {
  try {
    console.log('Launching local Chromium with persistent context...');
    
    const userDataDir = '/tmp/leadpilot-chrome-profile';
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });
    
    console.log('Navigating to Facebook login...');
    const page = await context.newPage();
    
    // First try to check if we're already logged in
    await page.goto('https://www.facebook.com', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);
    
    const url = page.url();
    console.log(`Current URL: ${url}`);
    
    // Check cookies
    const allCookies = await context.cookies();
    const fbCookies = allCookies.filter(c => c.domain.includes('facebook.com') || c.domain.includes('.facebook.com'));
    
    console.log(`\nFound ${fbCookies.length} Facebook cookies`);
    
    const c_user = fbCookies.find(c => c.name === 'c_user');
    const xs = fbCookies.find(c => c.name === 'xs');
    
    console.log(`c_user: ${c_user ? c_user.value : 'NOT FOUND ❌'}`);
    console.log(`xs: ${xs ? xs.value : 'NOT FOUND ❌'}`);
    
    if (c_user && xs) {
      // Save cookies
      const fs = require('fs');
      const outputPath = '/home/user/fb_data/cookies_fresh.json';
      fs.writeFileSync(outputPath, JSON.stringify({
        c_user: c_user.value,
        xs: xs.value,
        cookieArray: [
          { name: 'c_user', value: c_user.value, domain: '.facebook.com', path: '/' },
          { name: 'xs', value: xs.value, domain: '.facebook.com', path: '/' },
        ]
      }, null, 2));
      console.log(`\n✅ Cookies saved to: ${outputPath}`);
    } else {
      console.log('\n❌ Not logged into Facebook. Need interactive login.');
      // Save page screenshot for debugging
      await page.screenshot({ path: '/home/user/fb_data/fb_login_state.png', fullPage: false });
      console.log('Screenshot saved to /home/user/fb_data/fb_login_state.png');
    }
    
    await context.close();
    console.log('Done.');
  } catch (err) {
    console.error('ERROR:', err.message);
    process.exit(1);
  }
})();
