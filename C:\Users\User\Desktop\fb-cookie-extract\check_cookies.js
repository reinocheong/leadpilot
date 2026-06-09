const { chromium } = require('playwright');

(async () => {
  try {
    const browser = await chromium.connectOverCDP('http://localhost:9222');
    console.log('Connected!');
    
    const contexts = browser.contexts();
    console.log(`Found ${contexts.length} contexts`);
    
    for (let i = 0; i < contexts.length; i++) {
      const ctx = contexts[i];
      const pages = ctx.pages();
      console.log(`Context ${i}: ${pages.length} pages`);
      
      for (let p = 0; p < pages.length; p++) {
        console.log(`  Page ${p}: "${await pages[p].title()}" -> ${pages[p].url()}`);
      }
      
      const allCookies = await ctx.cookies();
      console.log(`  Total cookies: ${allCookies.length}`);
      
      const fbCookies = allCookies.filter(c => c.domain.includes('facebook'));
      console.log(`  Facebook cookies: ${fbCookies.length}`);
      
      for (const c of fbCookies.slice(0, 20)) {
        console.log(`    ${c.name}: ${c.value.substring(0, 20)}... (domain: ${c.domain})`);
      }
      
      const c_user = fbCookies.find(c => c.name === 'c_user');
      const xs = fbCookies.find(c => c.name === 'xs');
      console.log(`  c_user: ${c_user ? c_user.value : 'NOT FOUND'}`);
      console.log(`  xs: ${xs ? xs.value : 'NOT FOUND'}`);
    }
    
    await browser.close();
    console.log('\nDone.');
  } catch (err) {
    console.error('ERROR:', err.message);
    process.exit(1);
  }
})();
