// Launch Windows Chrome directly from WSL using Playwright
// This avoids the CDP remote debugging port entirely
const { chromium } = require('playwright');

(async () => {
  try {
    console.log('Launching Windows Chrome with Playwright...');
    
    const userDataDir = '/mnt/c/Users/User/AppData/Local/Google/Chrome/User Data';
    const chromePath = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe';
    
    // Check if paths exist
    const fs = require('fs');
    if (!fs.existsSync(chromePath)) {
      console.error(`Chrome not found at: ${chromePath}`);
      process.exit(1);
    }
    console.log(`Chrome found at: ${chromePath}`);
    
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: true,
      executablePath: chromePath,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-gpu',
        '--disable-dev-shm-usage',
      ],
    });
    
    console.log('Browser launched. Navigating to Facebook...');
    const page = await context.newPage();
    
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
      console.log('\n❌ Not logged into Facebook.');
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
