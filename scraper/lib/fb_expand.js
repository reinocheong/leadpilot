// fb_expand.js — Click all Facebook "展开" / "See More" buttons
// Uses TreeWalker + dispatchEvent to avoid Playwright DOM roundtrips (FB bot detection)

/**
 * Click all expand buttons on the current page.
 * Uses TreeWalker to find leaf elements with exact text match.
 * Runs two passes: first pass clicks all, second pass catches any
 * newly-revealed buttons.
 *
 * @param {import('playwright').Page} page
 * @returns {Promise<number>} total clicks performed
 */
async function clickExpandButtons(page) {
  const TARGET_TEXTS = ['\u5c55\u5f00', 'See More', 'See more']; // 展开
  let totalClicked = 0;

  try {
    // Pass 1: Click all visible expand buttons + inject CSS
    const pass1 = await page.evaluate((targets) => {
      // CSS injection to un-hide .text_exposed_show
      const style = document.createElement('style');
      style.textContent = '.text_exposed_show { display: inline !important; }';
      document.head.appendChild(style);

      function clickAll() {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
        let node, clicked = 0;
        while (node = walker.nextNode()) {
          // Only target leaf elements (≤3 children)
          if (node.querySelectorAll('*').length > 3) continue;
          const text = (node.textContent || '').trim();
          if (targets.includes(text)) {
            try {
              node.dispatchEvent(new MouseEvent('click', {
                bubbles: true, cancelable: true, view: window
              }));
              clicked++;
            } catch (e) { /* element removed mid-walk */ }
          }
        }
        return clicked;
      }
      return clickAll();
    }, TARGET_TEXTS);

    totalClicked += pass1;

    // Wait for React to process clicks and render expanded content
    await page.waitForTimeout(2000);

    // Pass 2: Catch newly-revealed expand buttons
    const pass2 = await page.evaluate((targets) => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
      let node, clicked = 0;
      while (node = walker.nextNode()) {
        if (node.querySelectorAll('*').length > 3) continue;
        const text = (node.textContent || '').trim();
        if (targets.includes(text)) {
          try {
            node.dispatchEvent(new MouseEvent('click', {
              bubbles: true, cancelable: true, view: window
            }));
            clicked++;
          } catch (e) { /* element removed */ }
        }
      }
      return clicked;
    }, TARGET_TEXTS);

    totalClicked += pass2;
  } catch (e) {
    console.log(`[expand] Non-fatal error: ${e.message}`);
  }

  return totalClicked;
}

module.exports = { clickExpandButtons };
