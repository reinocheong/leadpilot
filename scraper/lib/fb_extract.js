// fb_extract.js — Extract post data from Facebook group page
// Finds all [role="article"] elements, extracts text, agent name, and post link.

/**
 * Extract posts from the current page state.
 * Only keeps elements that have a real post permalink (filters out UI sub-elements).
 *
 * @param {import('playwright').Page} page
 * @param {string} groupId
 * @returns {Promise<Array<{agentName: string, text: string, postLink: string}>>}
 */
async function extractPosts(page, groupId) {
  return page.evaluate((gid) => {
    const articles = document.querySelectorAll('[role="article"]');
    const results = [];

    // FB generated username: two+ CamelCase words glued together
    const isFbGeneratedName = (name) => /^[A-Z][a-z]{3,}[A-Z][a-z]{3,}\d*$/.test(name);

    for (const article of articles) {
      const text = (article.textContent || '').trim();

      // Skip too-short posts and known spam
      if (text.length < 40) continue;
      if (/^你的\d+年wira/.test(text)) continue;

      // --- Step 1: Extract post permalink first ---
      // If no real post link found, this is likely a UI element (like/share/comment bar)
      // not the actual post — skip it.
      let postLink = '';
      for (const link of article.querySelectorAll('a')) {
        const href = link.href || '';
        const pm = href.match(/\/(posts|permalink)\/(\d{6,})/);
        if (pm) {
          postLink = `https://www.facebook.com/groups/${gid}/posts/${pm[2]}`;
          break;
        }
      }
      // Fallback: try shorter post ID pattern
      if (!postLink) {
        for (const link of article.querySelectorAll('a')) {
          const pm = (link.href || '').match(/\/posts\/(\d+)/);
          if (pm) {
            postLink = `https://www.facebook.com/groups/${gid}/posts/${pm[1]}`;
            break;
          }
        }
      }
      // No post link = not a real post element → skip
      if (!postLink) continue;

      // --- Step 2: Extract agent name from start of text ---
      let agentName = '';

      // Strategy 1: "Name · 关注/回复/分享/新秀" — Chinese or English name before "关注"
      // e.g., "黄苇鸿 · 关注1小时 · 分享对象：" or "Kun Yee Lee · 关注新秀贡献者 · 3小时"
      let m = text.match(/^([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z\s]{1,25}?)\s*[·•]\s*(?:关注|回复|分享|新秀)/);
      if (m) agentName = m[1].trim();

      // Strategy 2: Name directly followed by time digit (no space)
      // e.g., "Bread Coffee20小时 ·", "Annie Annie7小时 ·", "Genki Yap1小时 ·"
      if (!agentName) {
        m = text.match(/^([A-Za-z\u4e00-\u9fff][\sA-Za-z\u4e00-\u9fff]{1,25}?)\s*(?:\d{1,2}\s*(?:小时|分钟|秒|天|周|月|年|日)|刚刚)/);
        if (m) agentName = m[1].trim();
      }

      // Strategy 3: Name directly before Chinese date (月/日)
      // e.g., "Bibi Wong5月13日16:52 ·"
      if (!agentName) {
        m = text.match(/^([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z\s]{1,25}?)\s*\d{1,2}月\d{1,2}日/);
        if (m) agentName = m[1].trim();
      }

      // Strategy 4: English name within first 80 chars, before a separator
      if (!agentName) {
        m = text.substring(0, 80).match(/([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*[·•]/);
        if (m && !isFbGeneratedName(m[1])) agentName = m[1].trim();
      }

      // Strategy 5: Name followed by "新秀贡献者" (FB profile badge)
      // e.g., "Lau John新秀贡献者 · 3天", "Chin Choy Tan新秀贡献者 · 1天"
      if (!agentName) {
        m = text.match(/^([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z\s]{1,25}?)新秀贡献者/);
        if (m) agentName = m[1].trim();
      }

      // Strategy 6: English name directly before Chinese text (common FB post openers)
      // e.g., "Fang Gan你好，我是屋主", "Tracy Yap彩虹花园"
      if (!agentName) {
        m = text.match(/^([A-Z][a-z]+(?:[\s'][A-Z][a-z]+){0,3})\s*([\u4e00-\u9fff])/);
        if (m && !isFbGeneratedName(m[1])) agentName = m[1].trim();
      }

      // Strategy 7: English name directly before "天赞回复" / "赞回复" / similar
      // e.g., "Edward Ta Chen TanPandan residence 1 房 全家私 Rm15003天赞回复分享"
      if (!agentName) {
        m = text.match(/^([A-Z][a-z]+(?:[\s'][A-Z][a-z]+){0,3}).{0,20}天?赞回复/);
        if (m && !isFbGeneratedName(m[1])) agentName = m[1].trim();
      }

      // Filter FB generated usernames
      if (agentName && isFbGeneratedName(agentName)) {
        agentName = '';
      }

      // FB anonymous placeholder — keep it as-is (not an error)
      if (agentName === '匿名互动者') {
        // valid FB behavior, no action needed
      }

      results.push({ agentName, text, postLink });
    }
    return results;
  }, groupId);
}

module.exports = { extractPosts };
