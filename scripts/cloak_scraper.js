#!/usr/bin/env node
/**
 * CloakBrowser FB Group Scraper
 * Uses residential proxies + anti-detection to bypass FB headless restrictions
 * 
 * Reads cookies from /home/user/fb_data/cookies_fresh.json
 * Saves output to /home/user/fb_data/fb_posts_raw.json
 */

// The actual scraping code that runs inside CloakBrowser
const SCRAPE_CODE = async (page) => {
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

  const COOKIES = [
    {"name":"dbln","value":"%7B%2261590420160900%22%3A%22fEDBfk6W%22%7D","domain":".facebook.com","path":"/login/device-based/","sameSite":"None"},
    {"name":"datr","value":"AO0fasl2xt-GUYBk05qBF-EC","domain":".facebook.com","path":"/"},
    {"name":"sb","value":"AO0farJhdlEYxbVTp1sk1Vho","domain":".facebook.com","path":"/"},
    {"name":"locale","value":"zh_CN","domain":".facebook.com","path":"/"},
    {"name":"ps_l","value":"1","domain":".facebook.com","path":"/","sameSite":"Lax"},
    {"name":"ps_n","value":"1","domain":".facebook.com","path":"/","sameSite":"None"},
    {"name":"wd","value":"929x917","domain":".facebook.com","path":"/","sameSite":"Lax"},
    {"name":"c_user","value":"61590420160900","domain":".facebook.com","path":"/"},
    {"name":"xs","value":"26%3A7FRVqMQbaupcsg%3A2%3A1780994156%3A-1%3A-1%3A%3AAcxmwp10wQjWLkdpX4bP9u1UEnZbKV707OUtv4BKwA","domain":".facebook.com","path":"/"},
    {"name":"fr","value":"1IpJAeSwLODGCm4jo.AWf7UI98_B67sgYa_MwpUF_1Pm0nGH7XvUKkfM37YwASUQfvJLM.BqJ_vd..AAA.0.0.BqKAfS.AWeOPV-HC9s0u7oLINZ7DL3Ew0U","domain":".facebook.com","path":"/"},
    {"name":"presence","value":"C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1781008342546%2C%22v%22%3A1%7D","domain":".facebook.com","path":"/","sameSite":"Lax"},
  ];

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  
  // Helper: extract phone from text
  const extractPhone = (text) => {
    const phones = text.match(/(?:\+?6?0?1)[0-9\- ]{7,12}/g);
    return phones ? phones[0].trim() : '';
  };

  // Helper: extract agent name from FB article
  const extractAgentName = (article, text) => {
    let agentName = '';
    let m;
    // Strategy 1: "Name · 关注/回复/分享/新秀"
    m = text.match(/^([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z\s]{1,25}?)\s*[·•]\s*(?:关注|回复|分享|新秀)/);
    if (m) agentName = m[1].trim();
    // Strategy 2: Name + time
    if (!agentName) {
      m = text.match(/^([A-Za-z\u4e00-\u9fff][\sA-Za-z\u4e00-\u9fff]{1,25}?)\s*(?:\d{1,2}\s*(?:小[时時]|分[钟鐘]|秒|[天周月年日])|刚刚)/);
      if (m) agentName = m[1].trim();
    }
    // Strategy 3: Try getting from link text inside article
    if (!agentName) {
      const links = article.querySelectorAll('a');
      for (const link of links) {
        const href = link.href || '';
        if (href.includes('/user/') || href.includes('/profile.php')) {
          agentName = link.textContent.trim();
          break;
        }
      }
    }
    return agentName;
  };

  // Inject cookies
  await page.context().addCookies(COOKIES);

  let allPosts = [];
  let groupIndex = 0;

  for (const g of GROUPS) {
    groupIndex++;
    const url = `https://www.facebook.com/groups/${g.id}?sorting_setting=RECENT_ACTIVITY`;
    console.log(`[${groupIndex}/${GROUPS.length}] ${g.name}...`);

    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
      await sleep(4000);

      // Scroll to load more posts (8 scrolls)
      for (let s = 0; s < 8; s++) {
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await sleep(2000);
      }

      // Extract posts
      const posts = await page.evaluate((gid, phoneFn, nameFn) => {
        const articles = document.querySelectorAll('[role="article"]');
        const results = [];
        const seen = new Set();
        
        for (const article of articles) {
          const text = (article.textContent || '').trim();
          if (text.length < 40) continue;
          if (/^你的\d+年wira/.test(text)) continue;

          // Find post link
          let postLink = '';
          for (const link of article.querySelectorAll('a')) {
            const href = link.href || '';
            const pm = href.match(/\/posts\/(\d+)/);
            if (pm && !href.includes('comment_id')) {
              postLink = `https://www.facebook.com/groups/${gid}/posts/${pm[1]}`;
              break;
            }
          }
          if (!postLink) continue;
          if (seen.has(postLink)) continue;
          seen.add(postLink);

          const agentName = nameFn(article, text);
          const phone = phoneFn(text);

          results.push({
            group_id: gid,
            group_name: '',
            agent_name: agentName,
            text: text.substring(0, 3000),
            phone: phone,
            link: postLink,
            scraped_at: new Date().toISOString(),
          });
        }
        return results;
      }, g.id, extractPhone, extractAgentName);

      // Patch group name
      posts.forEach(p => p.group_name = g.name);
      allPosts = allPosts.concat(posts);
      console.log(`  -> ${posts.length} posts`);

      // Save after each group (partial progress)
      // Note: this runs in browser context, can't write files directly
      // Will be passed back in return value

    } catch (err) {
      console.log(`  -> Error: ${err.message}`);
    }
  }

  return { total: allPosts.length, posts: allPosts };
};
