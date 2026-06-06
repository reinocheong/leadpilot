const fs = require('fs');
const { extractPhone } = require('./lib/fb_phone');
const { clickExpandButtons } = require('./lib/fb_expand');
const { extractPosts } = require('./lib/fb_extract');
const { launchBrowser, isBrowserDeadError } = require('./lib/browser');

const COOKIES = [
  { name: 'c_user', value: '61590420160900', domain: '.facebook.com', path: '/' },
  { name: 'xs', value: '40%3AyLyhOJU9s6y-7A%3A2%3A1780729726%3A-1%3A-1%3A%3AAczuDnShlPNc0jH1apr45-WY9Dtktn7lF5-KtihycA', domain: '.facebook.com', path: '/' },
  { name: 'fr', value: '1bLDr7nrXnTWDvKM5.AWfe6IIGL3q_ewtZ31S8536DA3776y9ou5V5PYDFuiIKLsaDSJs.BqI8eB..AAA.0.0.BqI8fp.AWe6Ru1aplYVlnux6VaEhWjzJ0s', domain: '.facebook.com', path: '/' },
];
const GROUPS = [
  { id: '1467428250213843', name: 'JB新山租房与出租' },
  { id: '1729282070619968', name: 'Group2' },
  { id: '858717724308696', name: 'JB Property For Sales/Rent' },
  { id: '457010468361601', name: 'Group4' },
  { id: '801784763175081', name: 'Group3-房屋出租' },
  { id: '290627785937141', name: 'Group5-租屋' },
  { id: '1146057718813207', name: 'Group6' },
  { id: '1918174271803095', name: 'Group7' },
];
const OUTPUT_JSON = '/home/user/fb_data/fb_posts_raw.json';
const MAX_SCROLL_ATTEMPTS = 4;
const SCROLL_WAIT_MS = 1500;

/** Scroll until no new content loads (stops when page height stops growing). */
async function scrollToLoadPosts(page) {
  let prevHeight = 0;
  let stuckCount = 0;
  for (let i = 0; i < MAX_SCROLL_ATTEMPTS; i++) {
    const curHeight = await page.evaluate(() => document.body.scrollHeight);
    if (curHeight === prevHeight) {
      stuckCount++;
      if (stuckCount >= 2) break; // no new content after 2 tries
    } else {
      stuckCount = 0;
    }
    prevHeight = curHeight;
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(SCROLL_WAIT_MS);
  }
}

async function scrapeGroup(browser, groupId, groupName) {
  console.log(`[scraper/fb_scraper.js][${groupName}] 开始抓取`);
  let context = null, page = null, posts = [];
  let timedOut = false;
  const PAGE_GOTO_TIMEOUT = 120000;   // 2min for page load (FB is slow)
  const TIMEOUT_MS = 180000;          // 3min per group max
  try {
    context = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36', locale: 'en-US' });
    await context.addCookies(COOKIES);
    page = await context.newPage();
    await page.goto(`https://www.facebook.com/groups/${groupId}?sorting_setting=RECENT_ACTIVITY`, { waitUntil: 'domcontentloaded', timeout: PAGE_GOTO_TIMEOUT });
    await page.waitForTimeout(3000);
    // Race: scrape with a per-group timeout so one slow group can't hang the whole run
    await Promise.race([
      (async () => {
        await scrollToLoadPosts(page);
        const pre = await extractPosts(page, groupId);
        await clickExpandButtons(page);
        await page.waitForTimeout(1500);
        const post = await extractPosts(page, groupId);
        const seen = new Set();
        post.forEach(p => { if(p.postLink) seen.add(p.postLink); posts.push(buildPost(groupId, groupName, p)); });
        pre.forEach(p => { if(!seen.has(p.postLink)) posts.push(buildPost(groupId, groupName, p)); });
      })(),
      new Promise((_, reject) => setTimeout(() => { timedOut = true; reject(new Error('Group scrape timed out')); }, TIMEOUT_MS))
    ]);
    if (!timedOut) console.log(`[scraper/fb_scraper.js][${groupName}] 结束: 抓取到 ${posts.length} 条`);
  } catch (e) {
    if (!timedOut) fs.appendFileSync('/home/user/leadpilot/.logs/error.log', `[${new Date().toISOString()}] [scraper/fb_scraper.js] [scrapeGroup] -> ${e.stack}\n`);
    console.log(`[scraper/fb_scraper.js][${groupName}] ${timedOut ? '超时' : '失败'}: ${e.message}`);
    if (!timedOut && isBrowserDeadError(e.message)) throw e;
  } finally { if(page) await page.close(); if(context) await context.close(); }
  return posts;
}

function buildPost(groupId, groupName, p) {
  return { group_id: groupId, group_name: groupName, agent_name: p.agentName, text: p.text.substring(0, 3000), phone: extractPhone(p.text), link: p.postLink || `https://www.facebook.com/groups/${groupId}`, scraped_at: new Date().toISOString() };
}

(async () => {
  console.log('[scraper/fb_scraper.js][main] 开始');
  let allPosts = [], browser = null;
  for (const g of GROUPS) {
    let attempts = 0;
    while (attempts < 2) {
      attempts++;
      try {
        if (!browser || !browser.isConnected()) {
          if (browser) await browser.close().catch(() => {});
          browser = await launchBrowser();
        }
        const p = await scrapeGroup(browser, g.id, g.name);
        allPosts = allPosts.concat(p || []);
        // Save after each group so partial results aren't lost on interruption
        if (allPosts.length > 0) fs.writeFileSync(OUTPUT_JSON, JSON.stringify(allPosts, null, 2));
        break; // success — exit retry loop
      } catch (e) {
        console.log(`[scraper/fb_scraper.js][${g.name}] 第${attempts}次失败: ${e.message}${attempts < 2 ? '，重试...' : ''}`);
        if (browser) await browser.close().catch(() => {});
        browser = null;
        if (attempts < 2) await new Promise(r => setTimeout(r, 5000)); // wait 5s before retry
      }
    }
  }
  if (browser) await browser.close();
  if (allPosts.length > 0) fs.writeFileSync(OUTPUT_JSON, JSON.stringify(allPosts, null, 2));
  console.log(`[scraper/fb_scraper.js][main] 结束: 共抓取 ${allPosts.length} 条`);
})();
