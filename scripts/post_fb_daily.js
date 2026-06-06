#!/usr/bin/env node
/**
 * FB 每日发帖脚本 — 发到个人主页 timeline
 * 用法: node scripts/post_fb_daily.js [day_offset=0]
 * 配合 cron 每日运行
 */
const fs = require('fs');
const { launchBrowser } = require('../scraper/lib/browser');

const COOKIES = [
  { name: 'c_user', value: '61590420160900', domain: '.facebook.com', path: '/' },
  { name: 'xs', value: '40%3AyLyhOJU9s6y-7A%3A2%3A1780729726%3A-1%3A-1%3A%3AAczuDnShlPNc0jH1apr45-WY9Dtktn7lF5-KtihycA', domain: '.facebook.com', path: '/' },
  { name: 'fr', value: '1bLDr7nrXnTWDvKM5.AWfe6IIGL3q_ewtZ31S8536DA3776y9ou5V5PYDFuiIKLsaDSJs.BqI8eB..AAA.0.0.BqI8fp.AWe6Ru1aplYVlnux6VaEhWjzJ0s', domain: '.facebook.com', path: '/' },
];

// ── 7 篇轮换内容（中文，JB agent 视角） ──
const POSTS = [
  // Day 1
`做中介最怕的是什么？明明有客户找某个楼盘的房，你却不知道谁在卖。

我每天花半小时扫 5 个 FB 租房群，把放盘的 agent 和电话整理到一个表里。搜一个楼盘名，5 秒就知道谁在放盘，直接 WhatsApp 过去谈 cobroke。

省下来的时间，多谈几单不好吗？`,
  // Day 2
`JB 租房市场现在到底怎样？
我统计了这周 5 个主要 FB 群的数据：

🏠 最活跃楼盘：
• R&F Princess Cove — 13 条
• Bukit Indah — 11 条
• Mount Austin — 9 条
• Taman Pelangi — 8 条

💰 租金范围：RM450 - RM7,000
📈 中位数：RM1,900

数据每天自动更新。想查哪个楼盘？留言我帮你查。`,
  // Day 3
`做了几年中介，发现一个规律：
Cobroke 单成不成功，80% 取决于你够不够快看到盘。

别人刷 FB 群组等帖子出现，我用工具 30 分钟自动抓一次。新盘一出，马上能查到谁放盘、电话多少。

快一步，就多一单。`,
  // Day 4
`新山中介朋友，问你们一个问题：

你手上有没有那种放了两个月还没租出去的盘？

很多时候不是价格问题，是曝光不够。我这边每天有 agent 在找 cobroke，你的盘可能就是他们在找的。

有兴趣可以聊聊，免费帮你把盘推给更多 agent。`,
  // Day 5
`今日 JB 租房小贴士 🏠

很多屋主喜欢在帖子写 "PM me" 不留电话。
作为中介，看到这种帖子怎么办？

我的做法：截图存着，过两天再看一次。如果还没租出去，说明屋主可能急了，这时候直接留言或私信问 cobroke 机会，成功率更高。

你们有什么自己的小技巧？留言交流。`,
  // Day 6
`分享一个实用小工具 🔧

我做了个 JB 租房数据库，自动抓 5 个 FB 群组的放盘信息，带 agent 名字和电话。

免费试用 3 天，Google 登录就行。

👉 leadpilot.smart-tenancy-pro.org

有用的话帮我分享给其他 agent 朋友 🙏`,
  // Day 7
`这周 JB 中介圈最活跃的几个区：

1️⃣ Bukit Indah — 持续有量，condo 和 landed 都多
2️⃣ Mount Austin — 房间出租为主，学生客多
3️⃣ R&F / Danga Bay — 高端盘，cobroke 机会大
4️⃣ Taman Pelangi — 老区但稳定
5️⃣ Kulai / 古来 — 最近帖子在增加，值得关注

大家觉得哪个区最好做？留言说说你的看法。`,
];

function getTodayPost(dayOffset = 0) {
  const today = new Date();
  today.setDate(today.getDate() + dayOffset);
  const dayIndex = today.getDay(); // 0=Sun ... 6=Sat
  // Mon-Sat: 6 unique posts, Sunday repeats best one
  const idx = dayIndex === 0 ? (today.getDate() % 6) : dayIndex - 1;
  return POSTS[idx % POSTS.length];
}

async function postToFB(message) {
  console.log(`[fb_post] 准备发布 (${message.length}字)`);
  const browser = await launchBrowser({ headless: true });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
  });
  await ctx.addCookies(COOKIES);
  const page = await ctx.newPage();

  try {
    // 1. Navigate to own profile
    console.log('[fb_post] 打开 profile...');
    await page.goto('https://www.facebook.com/me', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(5000);

    // 2. Click the composer button
    console.log('[fb_post] 查找发帖按钮...');
    const composeBtn = await page.$('div[aria-label*="发布到你的个人主页"], div[aria-label*="个人主页"]');
    if (!composeBtn) throw new Error('找不到发帖按钮');
    await composeBtn.click();
    console.log('[fb_post] 已点击发帖按钮');
    await page.waitForTimeout(3000);

    // 3. Find the text editor in the popup
    console.log('[fb_post] 查找文字输入框...');
    const editor = await page.waitForSelector('[contenteditable="true"][aria-label*="在想"], [contenteditable="true"][aria-label*="What"], div[role="textbox"][contenteditable]', { timeout: 10000 })
      .catch(() => page.$('[contenteditable="true"]'));
    if (!editor) throw new Error('找不到文字输入框');

    // 4. Type the message
    await editor.click();
    await page.waitForTimeout(500);
    // Type character by character for reliability
    await editor.type(message, { delay: 20 });
    console.log('[fb_post] 已输入内容');
    await page.waitForTimeout(1000);

    // 5. Click Post button
    console.log('[fb_post] 查找发布按钮...');
    const postBtn = await page.$('div[aria-label="发布"][role="button"], div[aria-label*="Post"][role="button"], div[data-pagelet*="post"][role="button"]');
    if (!postBtn) throw new Error('找不到发布按钮');
    await postBtn.click();
    console.log('[fb_post] 已点击发布');
    
    // 6. Wait for post to complete
    await page.waitForTimeout(5000);
    
    // Verify - check if post appears (dialog closed)
    const dialogStillOpen = await page.$('div[role="dialog"]').catch(() => null);
    if (dialogStillOpen) {
      console.log('[fb_post] ⚠️ 对话框可能还没关');
    } else {
      console.log('[fb_post] ✅ 发布成功！');
    }

    // Log success
    const log = `[${new Date().toISOString()}] ✅ 发布成功 (${message.substring(0, 50)}...)\n`;
    fs.appendFileSync('/home/user/leadpilot/.logs/fb_post.log', log);

  } catch (e) {
    console.error(`[fb_post] ❌ 失败: ${e.message}`);
    const log = `[${new Date().toISOString()}] ❌ 失败: ${e.message}\n`;
    fs.appendFileSync('/home/user/leadpilot/.logs/fb_post.log', log);
    throw e;
  } finally {
    await browser.close().catch(() => {});
  }
}

// ── Main ──
const dayOffset = parseInt(process.argv[2] || '0');
const message = getTodayPost(dayOffset);
console.log(`[fb_post] Day offset: ${dayOffset}`);
console.log(`[fb_post] 内容预览: ${message.substring(0, 60)}...`);

postToFB(message).then(() => {
  console.log('[fb_post] 完成');
  process.exit(0);
}).catch(e => {
  console.error('[fb_post] 脚本失败:', e.message);
  process.exit(1);
});
