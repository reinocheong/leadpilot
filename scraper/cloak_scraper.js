#!/usr/bin/env node
/**
 * cloak_scraper.js — FB 群组爬虫（CloakBrowser 引擎 + 完整 stealth）
 *
 * 使用 cloakbrowser npm 包的 launch() + humanizeBrowser()，
 * 实现完整的反检测 stealth 层。
 *
 * Cookie：/home/user/fb_data/cookies_fresh.json（有 datr/sb 等完整 session）
 * 输出：/home/user/fb_data/fb_posts_raw.json
 */
const fs = require('fs');
const path = require('path');
const { launch, humanizeBrowser } = require('cloakbrowser');
const { extractPhone } = require('./lib/fb_phone');
const { extractPosts } = require('./lib/fb_extract');
const { clickExpandButtons } = require('./lib/fb_expand');

// ── Config ──────────────────────────────────────────────
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

function loadCookies() {
  const HARDCODED = [
    { name: 'c_user', value: '61590420160900', domain: '.facebook.com', path: '/' },
    { name: 'xs', value: '26%3A7FRVqMQbaupcsg%3A2%3A1780994156%3A-1%3A-1%3A%3AAcxmwp10wQjWLkdpX4bP9u1UEnZbKV707OUtv4BKwA', domain: '.facebook.com', path: '/' },
    { name: 'fr', value: '1IpJAeSwLODGCm4jo.AWf7UI98_B67sgYa_MwpUF_1Pm0nGH7XvUKkfM37YwASUQfvJLM.BqJ_vd..AAA.0.0.BqKAfS.AWeOPV-HC9s0u7oLINZ7DL3Ew0U', domain: '.facebook.com', path: '/' },
  ];
  try {
    const p = '/home/user/fb_data/cookies_fresh.json';
    if (fs.existsSync(p)) {
      const d = JSON.parse(fs.readFileSync(p, 'utf8'));
      if (d.fullCookieArray && d.fullCookieArray.length > 3) {
        console.log(`[cloak] 加载 ${d.fullCookieArray.length} 个 cookie`);
        return d.fullCookieArray;
      }
    }
  } catch (_) {}
  console.log('[cloak] 使用硬编码 cookie (最小集)');
  return HARDCODED;
}

function logError(msg) {
  const ts = new Date().toISOString();
  fs.appendFileSync('/home/user/leadpilot/.logs/error.log', `[${ts}] [cloak_scraper] ${msg}\n`);
}

async function scrapeGroup(browser, gid, gname) {
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    locale: 'en-US',
  });
  await context.addCookies(COOKIES);
  const page = await context.newPage();

  try {
    await page.goto(`https://www.facebook.com/groups/${gid}?sorting_setting=RECENT_ACTIVITY`, {
      waitUntil: 'domcontentloaded', timeout: 60000,
    });
    await page.waitForTimeout(5000);

    for (let s = 0; s < SCROLL_TIMES; s++) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(SCROLL_WAIT_MS);
    }

    const pre = await extractPosts(page, gid);
    await clickExpandButtons(page);
    await page.waitForTimeout(1500);
    const post = await extractPosts(page, gid);

    const seen = new Set();
    const all = [];
    const push = (p) => {
      if (!p.postLink || seen.has(p.postLink)) return;
      seen.add(p.postLink);
      all.push({
        group_id: gid, group_name: gname, agent_name: p.agentName,
        text: p.text.substring(0, 3000), phone: extractPhone(p.text),
        link: p.postLink, scraped_at: new Date().toISOString(),
      });
    };
    post.forEach(push);
    pre.forEach(push);

    console.log(`[cloak][${gname}] ${all.length} 条`);
    return all;
  } catch (e) {
    console.log(`[cloak][${gname}] 失败: ${e.message}`);
    logError(`${gname} -> ${e.message}`);
    return [];
  } finally {
    await page.close().catch(() => {});
    await context.close().catch(() => {});
  }
}

(async () => {
  console.log('[cloak] 启动 CloakBrowser (stealth)...');
  const browser = await launch({ headless: true });
  await humanizeBrowser(browser);

  console.log('[cloak] stealth 已应用，开始抓取...');
  const all = [];
  for (const g of GROUPS) {
    const posts = await scrapeGroup(browser, g.id, g.name);
    all.push(...posts);
    if (all.length > 0) fs.writeFileSync(OUTPUT_JSON, JSON.stringify(all, null, 2));
  }

  await browser.close().catch(() => {});
  if (all.length > 0) fs.writeFileSync(OUTPUT_JSON, JSON.stringify(all, null, 2));
  console.log(`[cloak] 完成: 共 ${all.length} 条 (${GROUPS.length} 群)`);
  process.exit(all.length > 0 ? 0 : 1);
})().catch(e => {
  console.error('[cloak] 致命:', e.message);
  logError(`致命: ${e.stack}`);
  process.exit(1);
});
