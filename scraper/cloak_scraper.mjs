#!/usr/bin/env node
import fs from 'fs';
import { launch, humanizeBrowser } from 'cloakbrowser';
import { extractPhone } from './lib/fb_phone.js';
import { extractPosts } from './lib/fb_extract.js';
import { clickExpandButtons } from './lib/fb_expand.js';

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
const SCROLL = 6;
const SCROLL_WAIT = 2000;

function loadCookies() {
  const H = [
    { name: 'c_user', value: '61590420160900', domain: '.facebook.com', path: '/' },
    { name: 'xs', value: '26%3A7FRVqMQbaupcsg%3A2%3A1780994156%3A-1%3A-1%3A%3AAcxmwp10wQjWLkdpX4bP9u1UEnZbKV707OUtv4BKwA', domain: '.facebook.com', path: '/' },
    { name: 'fr', value: '1IpJAeSwLODGCm4jo.AWf7UI98_B67sgYa_MwpUF_1Pm0nGH7XvUKkfM37YwASUQfvJLM.BqJ_vd..AAA.0.0.BqKAfS.AWeOPV-HC9s0u7oLINZ7DL3Ew0U', domain: '.facebook.com', path: '/' },
  ];
  try {
    const p = '/home/user/fb_data/cookies_fresh.json';
    if (fs.existsSync(p)) {
      const d = JSON.parse(fs.readFileSync(p, 'utf8'));
      if (d.fullCookieArray?.length > 3) {
        console.log(`[cloak] ${d.fullCookieArray.length} 个 cookie`);
        return d.fullCookieArray;
      }
    }
  } catch (_) {}
  console.log('[cloak] 硬编码 cookie');
  return H;
}

function logErr(m) {
  fs.appendFileSync('/home/user/leadpilot/.logs/error.log', `[${new Date().toISOString()}] [cloak] ${m}\n`);
}

async function scrapeGroup(browser, gid, gn) {
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/146.0.0.0 Safari/537.36',
    locale: 'en-US',
  });
  await ctx.addCookies(COOKIES);
  const page = await ctx.newPage();
  try {
    await page.goto(`https://www.facebook.com/groups/${gid}?sorting_setting=RECENT_ACTIVITY`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    for (let s = 0; s < SCROLL; s++) { await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await page.waitForTimeout(SCROLL_WAIT); }
    const pre = await extractPosts(page, gid);
    await clickExpandButtons(page);
    await page.waitForTimeout(1500);
    const post = await extractPosts(page, gid);
    const seen = new Set();
    const all = [];
    const push = (p) => { if (!p.postLink || seen.has(p.postLink)) return; seen.add(p.postLink); all.push({ group_id: gid, group_name: gn, agent_name: p.agentName, text: p.text.substring(0, 3000), phone: extractPhone(p.text), link: p.postLink, scraped_at: new Date().toISOString() }); };
    post.forEach(push); pre.forEach(push);
    console.log(`[cloak][${gn}] ${all.length} 条`);
    return all;
  } catch (e) {
    console.log(`[cloak][${gn}] ${e.message}`);
    logErr(`${gn} -> ${e.message}`);
    return [];
  } finally { await page.close().catch(() => {}); await ctx.close().catch(() => {}); }
}

(async () => {
  console.log('[cloak] 启动...');
  const browser = await launch({ headless: true });
  await humanizeBrowser(browser);
  console.log('[cloak] stealth ✓');

  const all = [];
  for (const g of GROUPS) {
    const p = await scrapeGroup(browser, g.id, g.name);
    all.push(...p);
    if (all.length) fs.writeFileSync(OUTPUT_JSON, JSON.stringify(all, null, 2));
  }
  await browser.close().catch(() => {});
  if (all.length) fs.writeFileSync(OUTPUT_JSON, JSON.stringify(all, null, 2));
  console.log(`[cloak] 完成: ${all.length} 条 (${GROUPS.length} 群)`);
  process.exit(all.length > 0 ? 0 : 1);
})().catch(e => { console.error('[cloak] 致命:', e.message); logErr(`致命: ${e.stack}`); process.exit(1); });
