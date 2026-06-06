#!/usr/bin/env node
/**
 * 一次性发帖 — 给 Reino 确认后执行
 */
const fs = require('fs');
const { launchBrowser } = require('../scraper/lib/browser');

const COOKIES = [
  { name: 'c_user', value: '61590420160900', domain: '.facebook.com', path: '/' },
  { name: 'xs', value: '40%3AyLyhOJU9s6y-7A%3A2%3A1780729726%3A-1%3A-1%3A%3AAczuDnShlPNc0jH1apr45-WY9Dtktn7lF5-KtihycA', domain: '.facebook.com', path: '/' },
  { name: 'fr', value: '1bLDr7nrXnTWDvKM5.AWfe6IIGL3q_ewtZ31S8536DA3776y9ou5V5PYDFuiIKLsaDSJs.BqI8eB..AAA.0.0.BqI8fp.AWe6Ru1aplYVlnux6VaEhWjzJ0s', domain: '.facebook.com', path: '/' },
];

const MESSAGE = process.argv[2];
if (!MESSAGE) {
  console.error('用法: node scripts/post_once.js "帖文内容"');
  process.exit(1);
}

(async () => {
  console.log(`[fb_post] 发布内容 (${MESSAGE.length}字)`);
  const browser = await launchBrowser({ headless: true });
  const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36' });
  await ctx.addCookies(COOKIES);
  const page = await ctx.newPage();

  try {
    // Go to profile
    console.log('[fb_post] 打开 profile...');
    await page.goto('https://www.facebook.com/me', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(8000);

    // Click composer
    console.log('[fb_post] 点击发帖按钮...');
    await page.waitForSelector('div[role="button"][aria-label*="个人主页"]', { timeout: 15000 });
    await page.click('div[role="button"][aria-label*="个人主页"]');
    await page.waitForTimeout(3000);

    // Find text editor
    console.log('[fb_post] 输入内容...');
    const editor = await page.waitForSelector('[contenteditable="true"]', { timeout: 10000 });
    await editor.click();
    await page.waitForTimeout(500);
    await editor.type(MESSAGE, { delay: 15 });

    // Click Post
    await page.waitForTimeout(1000);
    console.log('[fb_post] 点击发布...');
    const allButtons = await page.$$('div[role="button"]');
    let posted = false;
    for (const btn of allButtons) {
      const text = await btn.textContent().catch(() => '');
      if (text.trim() === '发布' || text.trim() === 'Post') {
        await btn.click();
        posted = true;
        break;
      }
    }
    if (!posted) throw new Error('找不到发布按钮');

    await page.waitForTimeout(5000);
    console.log('[fb_post] 发布成功!');
    fs.appendFileSync('/home/user/leadpilot/.logs/fb_post.log', `[${new Date().toISOString()}] 发布成功\n`);

  } catch (e) {
    console.error(`[fb_post] 失败: ${e.message}`);
    fs.appendFileSync('/home/user/leadpilot/.logs/fb_post.log', `[${new Date().toISOString()}] 失败: ${e.message}\n`);
    process.exit(1);
  } finally {
    await browser.close().catch(() => {});
  }
})();
