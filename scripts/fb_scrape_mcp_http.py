#!/usr/bin/env python3
"""
FB scraper via CloakBrowser MCP HTTP endpoint.
Batch-scrapes 8 FB groups (2 per batch), deduplicates, saves to file.
"""
import json
import os
import re
import sys
import urllib.request

MCP_URL = "http://127.0.0.1:30999/mcp"
OUTPUT_FILE = "/home/user/fb_data/fb_posts_raw.json"

GROUPS = [
    {"id": "1467428250213843", "name": "JB新山租房与出租"},
    {"id": "1729282070619968", "name": "Group2"},
    {"id": "858717724308696", "name": "JB Property For Sales/Rent"},
    {"id": "457010468361601", "name": "Group4"},
    {"id": "801784763175081", "name": "Group3-房屋出租"},
    {"id": "290627785937141", "name": "Group5-租屋"},
    {"id": "1146057718813207", "name": "Group6"},
    {"id": "1918174271803095", "name": "Group7"},
]

COOKIES = [
    {"name": "c_user", "value": "61590420160900", "domain": ".facebook.com", "path": "/"},
    {"name": "xs", "value": "26%3A7FRVqMQbaupcsg%3A2%3A1780994156%3A-1%3A-1%3A%3AAcxmwp10wQjWLkdpX4bP9u1UEnZbKV707OUtv4BKwA", "domain": ".facebook.com", "path": "/"},
    {"name": "fr", "value": "1IpJAeSwLODGCm4jo.AWf7UI98_B67sgYa_MwpUF_1Pm0nGH7XvUKkfM37YwASUQfvJLM.BqJ_vd..AAA.0.0.BqKAfS.AWeOPV-HC9s0u7oLINZ7DL3Ew0U", "domain": ".facebook.com", "path": "/"},
]


def mcp_call(session_id, method, params=None, timeout=300):
    """Send JSON-RPC to MCP server, return parsed result."""
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": int.from_bytes(os.urandom(4), 'big'),
        "method": method,
        "params": params or {}
    }).encode('utf-8')

    req = urllib.request.Request(
        MCP_URL, data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Session-Id": session_id
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode('utf-8')

    for line in raw.split('\n'):
        line = line.strip()
        if line.startswith('data: '):
            obj = json.loads(line[6:])
            if 'error' in obj:
                raise RuntimeError(f"MCP error: {obj['error']}")
            return obj.get('result')
    return None


def get_session():
    """Initialize a new MCP session."""
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "fb-scraper", "version": "1.0"}
        }
    }).encode('utf-8')
    req = urllib.request.Request(
        MCP_URL, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        sid = resp.headers.get('mcp-session-id', '')
        resp.read()
    return sid


def extract_result_text(result):
    """Extract the JSON result string from MCP tool response.

    The MCP returns markdown with:
        ### Result
        "<json_string>"
        ### Ran Playwright code
        ...
    Where <json_string> is a properly escaped JSON string value.
    We parse it with json.loads to handle all escaping correctly.
    """
    if not result:
        return None
    for item in result.get('content', []):
        if item.get('type') == 'text':
            text = item['text']
            # Split on ### markers to isolate the Result section
            parts = text.split('### Result')
            if len(parts) < 2:
                continue
            after_result = parts[1]
            # Split on next ### marker
            result_section = after_result.split('###')[0].strip()
            if not result_section:
                continue
            # result_section is a JSON string value like '"..."'
            # Parse it as JSON to properly unescape
            try:
                inner = json.loads(result_section)
                return inner
            except json.JSONDecodeError:
                continue
    return None


def build_code(groups_batch):
    """Build JS code for a batch of groups."""
    gjson = json.dumps(groups_batch, ensure_ascii=False)
    cjson = json.dumps(COOKIES)
    return f"""
async (page) => {{
  const GROUPS = {gjson};
  const COOKIES = {cjson};
  const ALL = [];
  const b = page.context().browser();
  
  for (const g of GROUPS) {{
    try {{
      const ctx = await b.newContext({{
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/146.0.0.0 Safari/537.36'
      }});
      await ctx.addCookies(COOKIES);
      const p = await ctx.newPage();
      await p.goto('https://www.facebook.com/groups/' + g.id + '?sorting_setting=RECENT_ACTIVITY', {{
        waitUntil: 'domcontentloaded',
        timeout: 45000
      }});
      await p.waitForTimeout(4000);
      
      for (let s = 0; s < 6; s++) {{
        await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await p.waitForTimeout(2000);
      }}
      
      const posts = await p.evaluate(() => {{
        const items = document.querySelectorAll('div[role="article"]');
        return Array.from(items).slice(0, 60).map(el => {{
          const t = (el.textContent || '').trim().substring(0, 1500);
          const l = el.querySelectorAll('a[href*="/posts/"]');
          return {{ text: t, link: l[0]?.href || '' }};
        }}).filter(p => p.text.length > 80);
      }});
      
      ALL.push(...posts.map(p => ({{
        group_id: g.id,
        group_name: g.name,
        text: p.text,
        link: p.link,
        scraped_at: new Date().toISOString()
      }})));
      
      await p.close().catch(() => {{}});
      await ctx.close().catch(() => {{}});
    }} catch (e) {{}}
  }}
  
  return JSON.stringify({{ total: ALL.length, posts: ALL }});
}}
"""


def clean_link(url):
    """Dedup key: strip ?__cft__ and beyond."""
    idx = url.find('?__cft__')
    return url[:idx] if idx >= 0 else url


def main():
    print("Initializing MCP session...", file=sys.stderr)
    session_id = get_session()
    print(f"Session: {session_id}", file=sys.stderr)

    all_new_posts = []

    for i in range(0, len(GROUPS), 2):
        batch = GROUPS[i:i+2]
        names = [g['name'] for g in batch]
        print(f"\n--- Batch {i//2 + 1}/4: {', '.join(names)} ---", file=sys.stderr)

        code = build_code(batch)
        try:
            result = mcp_call(session_id, "tools/call", {
                "name": "browser_run_code_unsafe",
                "arguments": {"code": code}
            }, timeout=250)

            raw_json = extract_result_text(result)
            if raw_json:
                data = json.loads(raw_json)
                posts = data.get('posts', [])
                print(f"  Got {len(posts)} posts", file=sys.stderr)
                all_new_posts.extend(posts)
            else:
                print(f"  No result text found", file=sys.stderr)
                if result:
                    print(f"  Raw result keys: {list(result.keys())}", file=sys.stderr)
        except Exception as e:
            print(f"  Batch failed: {e}", file=sys.stderr)
            # Get a new session for next batch
            try:
                session_id = get_session()
                print(f"  New session: {session_id}", file=sys.stderr)
            except:
                pass

    print(f"\nTotal scraped this run: {len(all_new_posts)}", file=sys.stderr)

    # Read existing data
    existing = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            print(f"Existing: {len(existing)} posts", file=sys.stderr)
        except Exception as e:
            print(f"Read existing failed: {e}", file=sys.stderr)

    # Merge & dedup
    combined = existing + all_new_posts
    seen = {}
    for post in combined:
        key = clean_link(post.get('link', ''))
        if key in seen:
            if post.get('scraped_at', '') > seen[key].get('scraped_at', ''):
                seen[key] = post
        else:
            seen[key] = post

    deduped = list(seen.values())
    new_count = len(deduped) - len(existing)
    existing_set = {clean_link(p.get('link', '')) for p in existing}
    new_actual = sum(1 for p in all_new_posts if clean_link(p.get('link', '')) not in existing_set)

    print(f"After dedup: {len(deduped)} total ({new_actual} genuinely new)", file=sys.stderr)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"Saved to {OUTPUT_FILE}", file=sys.stderr)

    # One-line report (just this goes to the user)
    print(f"FB爬虫 +{new_actual}条新帖 · 共{len(deduped)}条")


if __name__ == '__main__':
    main()
