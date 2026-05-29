// fb_extract.js — Extract post data from Facebook group page
// Finds all [role="article"] elements, extracts text, agent name, and post link.

/**
 * Extract posts from the current page state.
 * Filters out posts shorter than 40 chars and known spam patterns.
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

    // Try to find a real name anywhere in the post text (Chinese or English)
    const findRealName = (text) => {
      // Chinese name: 2-4 Chinese chars, often followed by space or action word
      const m = text.match(/([\u4e00-\u9fff]{2,4})(?:\s*(?:分享|回复|赞|在|·|小时|分钟|秒|刚刚))/);
      if (m) return m[1];
      // English name: Capitalized First Last near start
      const m2 = text.match(/^.{0,50}?\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b/);
      if (m2 && !isFbGeneratedName(m2[1])) return m2[1];
      return '';
    };

    for (const article of articles) {
      const text = (article.textContent || '').trim();

      // Skip too-short posts and known spam
      if (text.length < 40) continue;
      if (/^你的\d+年wira/.test(text)) continue;

      // Extract agent name — try multiple strategies
      let agentName = '';

      // Strategy 1: name at start followed by time indicator (most common for FB posts)
      let m = text.match(/^([\u4e00-\u9fffA-Za-z][^\d•·\s]{1,20}?)(?:\s*\d|\s*[·•]|\s*(?:小时|分钟|秒|刚刚|天|周|月|年))/);
      if (m) agentName = m[1].trim();

      // Strategy 2: look for Chinese name (2-4 chars) followed by "分享" or "回复"
      if (!agentName) {
        m = text.match(/([\u4e00-\u9fff]{2,4})\s*(?:分享|回复|赞|在)/);
        if (m) agentName = m[1].trim();
      }

      // Strategy 3: English name pattern (not FB-generated) within first 60 chars
      if (!agentName) {
        m = text.substring(0, 60).match(/([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*(?:分享|回复|赞|·)/);
        if (m && !isFbGeneratedName(m[1])) agentName = m[1].trim();
      }

      // Filter FB generated usernames — try to find real name instead
      if (agentName && isFbGeneratedName(agentName)) {
        const real = findRealName(text);
        agentName = real || '';
      }

      // Extract Facebook post permalink
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

      results.push({ agentName, text, postLink });
    }
    return results;
  }, groupId);
}

module.exports = { extractPosts };
