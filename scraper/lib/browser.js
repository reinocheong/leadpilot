// browser.js — Launch Playwright Chromium with stealth-friendly args
const { chromium } = require('playwright');

async function launchBrowser() {
  console.log('[scraper/lib/browser.js][init] 启动浏览器');
  return chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--disable-infobars',
      '--window-size=1280,900',
    ],
  });
}

function isBrowserDeadError(errMsg) {
  return /(?:Target|browser|context).*(?:closed|been closed)/i.test(errMsg || '');
}

module.exports = { launchBrowser, isBrowserDeadError };
