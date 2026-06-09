#!/usr/bin/env node
/**
 * cloak_scraper.js — FB 群组爬虫（CloakBrowser 引擎）
 *
 * 替换旧的 headless Playwright 爬虫。
 * 使用 CloakBrowser 的 Chromium 二进制（反检测）+ 完整 cookie 集。
 * 解决「headless 被 FB 限流，每群只给 1 条」的问题。
 *
 * Cookie 文件：/home/user/fb_data/cookies_fresh.json（fallback 到硬编码最小集）
 * 输出文件：/home/user/fb_data/fb_posts_raw.json
 * 错误日志：.logs/error.log
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { extractPhone } = require('./lib/fb_phone');
const { extractPosts } = require('./lib/fb_extract');
const { clickExpandButtons } = require('./lib/fb_expand');

// ── Config ──────────────────────────────────────────────
const CLOAK_CHROME_PATH = '/home/user/.cloakbrowser/chromium-146.0.7680.177.5/chrome';

const COOKIES = loadCookies();
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
const SCROLL_TIMES = 6;
const SCROLL_WAIT_MS = 2000;

// ── Cookie loading ──────────────────────────────────────
function loadCookies() {
  const HARDCODED = [
    { name: 'c_user', value: '61590420160900', domain: '.facebook.com', path: '/' },
    { name: 'xs', value: '26%3A7FRVqMQbaupcsg%3A2%3A1780994156%3A-1%3A-1%3A%3AAcxmwp10wQjWLkdpX4bP9u1UEnZbKV707OUtv4BKwA', domain: '.facebook.com', path: '/' },
    { name: 'fr', value: '1IpJAeSwLODGCm4jo.AWf7UI98_B67sgYa_MwpUF_1Pm0nGH7XvUKkfM37YwASUQfvJLM.BqJ_vd..AAA.0.0.BqKAfS.AWeOPV-HC9s0u7oLINZ7DL3Ew0U', domain: '.facebook.com', path: '/' },
  ];
  try {
    const cookieFile = '/home/user/fb_data/cookies_fresh.json';
    if (fs.existsSync(cookieFile)) {
      const loaded = JSON.parse(fs.readFileSync(cookieFile, 'utf8'));
      if (loaded.fullCookieArray && loaded.fullCookieArray.length > 3) {
        console.log(`[cloak] 加载 ${loaded.fullCookieArray.length} 个 cookie (from ${cookieFile})`);
        return loaded.fullCookieArray;
      }
    }
  } catch (_) { /* fallback to hardcoded */ }
  console.log('[cloak] 使用硬编码 cookie (最小集)');
  return HARDCODED;
}

function logError(msg) {
  const ts = new Date().toISOString();
  fs.appendFileSync('/home/user/leadpilot/.logs/error.log', `[${ts}] [cloak_scraper] ${msg}\n`);
}

// ── Scrape one group ────────────────────────────────────
async function scrapeGroup(browser, groupId, groupName) {
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    locale: 'en-US',
  });
  await context.addCookies(COOKIES);
  const page = await context.newPage();

  try {
    await page.goto(`https://www.facebook.com/groups/${groupId}?sorting_setting=RECENT_ACTIVITY`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await page.waitForTimeout(5000);

    // Scroll to load posts
    for (let s = 0; s < SCROLL_TIMES; s++) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(SCROLL_WAIT_MS);
    }

    // Extract posts
    const posts = await extractPosts(page, groupId);
    await clickExpandButtons(page);
    await page.waitForTimeout(1500);
    const postsAfterExpand = await extractPosts(page, groupId);

    // Deduplicate by postLink
    const seen = new Set();
    const allPosts = [];
    const pushPost = (p) => {
      if (seen.has(p.postLink)) return;
      seen.add(p.postLink);
      allPosts.push({
        group_id: groupId,
        group_name: groupName,
        agent_name: p.agentName,
        text: p.text.substring(0, 3000),
        phone: extractPhone(p.text),
        link: p.postLink || `https://www.facebook.com/groups/${groupId}`,
        scraped_at: new Date().toISOString(),
      });
    };
    postsAfterExpand.forEach(pushPost);
    posts.forEach(pushPost);

    console.log(`[cloak][${groupName}] ${allPosts.length} 条`);
    return allPosts;
  } catch (e) {
    console.log(`[cloak][${groupName}] 失败: ${e.message}`);
    logError(`${groupName} -> ${e.message}`);
    return [];
  } finally {
    await page.close().catch(() => {});
    await context.close().catch(() => {});
  }
}

// ── Main ────────────────────────────────────────────────
(async () => {
  console.log('[cloak] 启动 CloakBrowser...');

  const browser = await chromium.launch({
    executablePath: CLOAK_CHROME_PATH,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--disable-infobars',
      '--window-size=1280,900',
    ],
  });

  const allPosts = [];
  for (const g of GROUPS) {
    const posts = await scrapeGroup(browser, g.id, g.name);
    allPosts.push(...posts);
    // Save after each group
    if (allPosts.length > 0) {
      fs.writeFileSync(OUTPUT_JSON, JSON.stringify(allPosts, null, 2));
    }
  }

  await browser.close().catch(() => {});

  if (allPosts.length > 0) {
    fs.writeFileSync(OUTPUT_JSON, JSON.stringify(allPosts, null, 2));
  }
  console.log(`[cloak] 完成: 共 ${allPosts.length} 条 (${GROUPS.length} 群)`);

  process.exit(allPosts.length > 0 ? 0 : 1);
})().catch(e => {
  console.error('[cloak] 致命错误:', e.message);
  logError(`致命错误: ${e.stack}`);
  process.exit(1);
});
