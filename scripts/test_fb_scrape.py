#!/usr/bin/env python3
"""Test MCP call to cloakbrowser - real FB scrape."""
import json
import urllib.request
import sys

MCP_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:30999/mcp"

# Get session
body0 = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
               "clientInfo": {"name": "fb-scraper", "version": "1.0"}}
}).encode('utf-8')

req0 = urllib.request.Request(MCP_URL, data=body0, headers={
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
})
with urllib.request.urlopen(req0, timeout=30) as resp:
    session_id = resp.headers.get('mcp-session-id', '')
    resp.read()  # discard body

print(f"Session: {session_id}", file=sys.stderr)

COOKIES = json.dumps([
    {"name": "c_user", "value": "61590420160900", "domain": ".facebook.com", "path": "/"},
    {"name": "xs", "value": "26%3A7FRVqMQbaupcsg%3A2%3A1780994156%3A-1%3A-1%3A%3AAcxmwp10wQjWLkdpX4bP9u1UEnZbKV707OUtv4BKwA", "domain": ".facebook.com", "path": "/"},
    {"name": "fr", "value": "1IpJAeSwLODGCm4jo.AWf7UI98_B67sgYa_MwpUF_1Pm0nGH7XvUKkfM37YwASUQfvJLM.BqJ_vd..AAA.0.0.BqKAfS.AWeOPV-HC9s0u7oLINZ7DL3Ew0U", "domain": ".facebook.com", "path": "/"},
])

GROUPS = [{"id": "1467428250213843", "name": "JB新山租房与出租"}]
groups_json = json.dumps(GROUPS)

code = f"""
async (page) => {{
  const GROUPS = {groups_json};
  const COOKIES = {COOKIES};
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
    }} catch (e) {{
      // Skip failed group
    }}
  }}
  
  return JSON.stringify({{ total: ALL.length, posts: ALL }});
}}
"""

print(f"Code length: {len(code)} chars", file=sys.stderr)

body = json.dumps({
    "jsonrpc": "2.0", "id": 10, "method": "tools/call",
    "params": {
        "name": "browser_run_code_unsafe",
        "arguments": {"code": code}
    }
}).encode('utf-8')

req = urllib.request.Request(MCP_URL, data=body, headers={
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": session_id
})

try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read().decode('utf-8')
    
    print(f"Response length: {len(raw)}", file=sys.stderr)
    
    # Parse SSE
    for line in raw.split('\n'):
        if line.startswith('data: '):
            obj = json.loads(line[6:])
            if 'error' in obj:
                print(f"MCP ERROR: {obj['error']}", file=sys.stderr)
                sys.exit(1)
            for item in obj.get('result', {}).get('content', []):
                if item.get('type') == 'text':
                    text = item['text']
                    # Extract JSON result from markdown
                    # The result is inside ### Result\n\"...\"
                    import re
                    m = re.search(r'### Result\s*\n(.+)', text)
                    if m:
                        result_str = m.group(1).strip()
                        # Unescape
                        result_str = result_str.replace('\\"', '"').replace('\\n', '\n')
                        # The result is a JSON string wrapped in double quotes
                        if result_str.startswith('"') and result_str.endswith('"'):
                            result_str = result_str[1:-1]
                        try:
                            data = json.loads(result_str)
                            print(f"Posts: {data.get('total', 0)}", file=sys.stderr)
                            if data.get('posts'):
                                for p in data['posts'][:3]:
                                    print(f"  - {p.get('group_name','')}: {p.get('text','')[:80]}...", file=sys.stderr)
                            print(json.dumps(data, ensure_ascii=False))
                        except json.JSONDecodeError as e:
                            print(f"JSON parse error: {e}", file=sys.stderr)
                            print(f"Raw result text: {text[:500]}", file=sys.stderr)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    if hasattr(e, 'read'):
        print("Body:", e.read().decode('utf-8')[:1000], file=sys.stderr)
