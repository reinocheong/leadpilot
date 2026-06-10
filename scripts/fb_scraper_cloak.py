#!/usr/bin/env python3
"""FB Group scraper using CloakBrowser — cron job for LeadPilot."""

import json
import os
import sys
import time
import re
from datetime import datetime, timezone

# ── Config ───────────────────────────────────────────────────────
COOKIE_FILE = "/home/user/fb_data/cookies_fresh.json"
RAW_FILE = "/home/user/fb_data/fb_posts_raw.json"

GROUPS = [
    ("1467428250213843", "JB新山租房与出租"),
    ("1729282070619968", "Group2"),
    ("858717724308696", "JB Property For Sales/Rent"),
    ("457010468361601", "Group4"),
    ("801784763175081", "Group3-房屋出租"),
    ("290627785937141", "Group5-租屋"),
    ("1146057718813207", "Group6"),
    ("1918174271803095", "Group7"),
]

SCROLL_COUNT = 6
SCROLL_DELAY = 2
WAIT_AFTER_NAV = 5

# ── Results Tracking ──────────────────────────────────────────────
results_by_group = {}  # group_id -> list of posts
errors = []


def load_cookies():
    with open(COOKIE_FILE) as f:
        data = json.load(f)
    # fullCookieArray contains the Playwright-compatible cookies
    cookies = data.get("fullCookieArray", [])
    # Ensure they have proper name/value
    result = []
    for c in cookies:
        entry = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".facebook.com"),
            "path": c.get("path", "/"),
            "secure": True,
            "httpOnly": False,
        }
        result.append(entry)
    return result


def load_existing():
    """Load existing raw posts, return dict keyed by link."""
    if not os.path.exists(RAW_FILE):
        return {}
    with open(RAW_FILE) as f:
        data = json.load(f)
    # Handle both list and {posts: [...]} format
    if isinstance(data, dict) and "posts" in data:
        posts = data["posts"]
    elif isinstance(data, list):
        posts = data
    else:
        posts = []
    by_link = {}
    for p in posts:
        if not isinstance(p, dict):
            continue
        link = p.get("link", "")
        if link:
            by_link[link] = p
    return by_link


def scrape_group(page, gid, gname, cookies):
    """Scrape a single FB group page, return list of posts."""
    posts = []
    url = f"https://www.facebook.com/groups/{gid}"

    try:
        # Inject cookies
        page.context.add_cookies(cookies)
        time.sleep(0.5)

        # Navigate
        print(f"  Navigating to {url}...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(WAIT_AFTER_NAV)

        # Scroll
        print(f"  Scrolling {SCROLL_COUNT} times...")
        for i in range(SCROLL_COUNT):
            page.evaluate("window.scrollBy(0, window.innerHeight * 1.5)")
            time.sleep(SCROLL_DELAY)

        # Extract articles
        print(f"  Extracting article data...")
        result = page.evaluate("""(params) => {
    const gid = params.gid;
    const gname = params.gname;
    const articles = document.querySelectorAll('div[role="article"]');
    const items = [];
    const seen = new Set();
    
    articles.forEach((article) => {
        // Find the post link
        const links = article.querySelectorAll('a[href*="/groups/"][href*="/posts/"]');
        let link = '';
        for (const a of links) {
            const href = a.getAttribute('href');
            if (href && href.includes('/posts/')) {
                link = href.startsWith('http') ? href : 'https://www.facebook.com' + href;
                break;
            }
        }
        if (!link || seen.has(link)) return;
        seen.add(link);
        
        // Clean link
        link = link.split('?')[0];
        
        // Extract text content
        let text = article.textContent || '';
        text = text.trim();
        
        // Extract photos
        const imgs = article.querySelectorAll('img');
        const photos = [];
        imgs.forEach((img) => {
            const src = img.getAttribute('src');
            if (src && src.startsWith('http') && !src.includes('static.xx.fbcdn') && img.offsetWidth > 50) {
                photos.push(src);
            }
        });
        
        items.push({
            group_id: gid,
            group_name: gname,
            text: text,
            photos: photos.slice(0, 10),
            link: link,
            scraped_at: new Date().toISOString(),
        });
    });
    
    return items;
}""", {"gid": gid, "gname": gname})

        print(f"  Found {len(result)} posts")
        posts = result

    except Exception as e:
        error_msg = f"  ERROR scraping {gname} ({gid}): {e}"
        print(error_msg)
        errors.append(error_msg)
        # Try to get a screenshot
        try:
            page.screenshot(path=f"/tmp/fb_error_{gid}.png")
        except:
            pass

    return posts


def merge_and_save(all_posts, existing_by_link, new_by_group):
    """Merge new posts with existing, dedup by link, save."""
    # Start with existing
    merged = list(existing_by_link.values())
    existing_links = set(existing_by_link.keys())

    new_count = 0
    dup_count = 0

    for gid, posts in new_by_group.items():
        for p in posts:
            link = p.get("link", "")
            if not link:
                continue
            if link in existing_links:
                dup_count += 1
            else:
                merged.append(p)
                existing_links.add(link)
                new_count += 1

    # Sort: group_id then scraped_at desc
    merged.sort(key=lambda x: (x.get("group_id", ""), x.get("scraped_at", "")))

    with open(RAW_FILE, "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n  Existing: {len(existing_by_link)}")
    print(f"  New: {new_count}")
    print(f"  Duplicates skipped: {dup_count}")
    print(f"  Total saved: {len(merged)}")

    return new_count


def main():
    print("=" * 60)
    print(f"FB Group Scraper — {datetime.now().isoformat()}")
    print("=" * 60)

    # Load cookies
    print("\n[1/3] Loading cookies...")
    cookies = load_cookies()
    print(f"  Cookie count: {len(cookies)}")

    # Load existing data
    print("\n[2/3] Loading existing data...")
    existing_by_link = load_existing()
    print(f"  Existing posts: {len(existing_by_link)}")

    # Import cloakbrowser
    from cloakbrowser import launch

    # Launch browser
    print("\n[3/3] Launching CloakBrowser...")
    browser = launch(headless=True, humanize=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 1920, "height": 1080})

    new_by_group = {}
    total_new = 0

    try:
        # Scrape each group
        for idx, (gid, gname) in enumerate(GROUPS, 1):
            print(f"\n── Group {idx}/{len(GROUPS)}: {gname} ({gid}) ──")
            posts = scrape_group(page, gid, gname, cookies)
            new_by_group[gid] = posts
            results_by_group[gid] = len(posts)

        # Merge and save — save as flat list for downstream compatibility
        print(f"\n{'='*60}")
        print("Saving merged data...")
        total_new = merge_and_save({}, existing_by_link, new_by_group)

    finally:
        browser.close()
        print("\nBrowser closed.")

    # ── Summary ──
    print(f"\n{'='*60}")
    print("SCRAPE SUMMARY")
    print(f"{'='*60}")
    for gid, gname in GROUPS:
        count = results_by_group.get(gid, 0)
        print(f"  {gname:35s} ({gid}): {count:3d} posts")
    print(f"  {'─'*50}")
    print(f"  {'TOTAL':35s}: {sum(results_by_group.values()):3d} posts")
    print(f"  {'New this run':35s}: {total_new:3d} posts")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    {e}")

    # Return summary for the cron output
    summary = {
        "groups_scraped": len(GROUPS),
        "groups_with_data": len([g for g in GROUPS if results_by_group.get(g[0], 0) > 0]),
        "total_posts": sum(results_by_group.values()),
        "new_posts": total_new,
        "errors": len(errors),
        "results_by_group": {g[1]: results_by_group.get(g[0], 0) for g in GROUPS},
    }

    print(f"\n{'='*60}")
    print("DONE")
    return summary


if __name__ == "__main__":
    summary = main()
    # Write summary for downstream
    with open("/tmp/fb_scrape_summary.json", "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
