#!/usr/bin/env python3
"""Debug MCP response."""
import json
import urllib.request

MCP_URL = "http://127.0.0.1:30999/mcp"

# Get session
body0 = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
               "clientInfo": {"name": "debug", "version": "1.0"}}
}).encode('utf-8')
req0 = urllib.request.Request(MCP_URL, data=body0, headers={
    "Content-Type": "application/json", "Accept": "application/json, text/event-stream"
})
with urllib.request.urlopen(req0, timeout=30) as resp:
    sid = resp.headers.get('mcp-session-id', '')
    resp.read()

print(f"Session: {sid}")

COOKIES = json.dumps([{"name":"c_user","value":"61590420160900","domain":".facebook.com","path":"/"}])
code = f"""
async (page) => {{
  const GROUPS = [{{"id":"1467428250213843","name":"JB新山租房与出租"}}];
  const COOKIES = {COOKIES};
  const ALL = [];
  const b = page.context().browser();
  for (const g of GROUPS) {{
    try {{
      const ctx = await b.newContext({{userAgent:'Mozilla/5.0'}});
      await ctx.addCookies(COOKIES);
      const p = await ctx.newPage();
      await p.goto('https://www.facebook.com/groups/'+g.id+'?sorting_setting=RECENT_ACTIVITY', {{waitUntil:'domcontentloaded',timeout:30000}});
      await p.waitForTimeout(3000);
      for(let s=0;s<3;s++){{await p.evaluate(()=>window.scrollTo(0,document.body.scrollHeight));await p.waitForTimeout(1500);}}
      const posts = await p.evaluate(()=>{{const items=document.querySelectorAll('div[role="article"]');return Array.from(items).slice(0,30).map(el=>{{const t=(el.textContent||'').trim().substring(0,1500);const l=el.querySelectorAll('a[href*="/posts/"]');return{{text:t,link:l[0]?.href||''}};}}).filter(p=>p.text.length>80);}});
      ALL.push(...posts.map(p=>({{group_id:g.id,group_name:g.name,text:p.text,link:p.link,scraped_at:new Date().toISOString()}})));
      await p.close().catch(()=>{{}});await ctx.close().catch(()=>{{}});
    }} catch(e){{}}
  }}
  return JSON.stringify({{total:ALL.length,posts:ALL}});
}}
"""

body = json.dumps({
    "jsonrpc": "2.0", "id": 10, "method": "tools/call",
    "params": {"name": "browser_run_code_unsafe", "arguments": {"code": code}}
}).encode('utf-8')

req = urllib.request.Request(MCP_URL, data=body, headers={
    "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": sid
})

with urllib.request.urlopen(req, timeout=250) as resp:
    raw = resp.read().decode('utf-8')

print(f"\nResponse length: {len(raw)}")
print("RAW (first 2000 chars):")
print(repr(raw[:2000]))
print("\n... (rest)")
print(repr(raw[2000:4000]))
