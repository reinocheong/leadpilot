#!/usr/bin/env python3
"""Test MCP call to cloakbrowser."""
import json
import urllib.request
import sys

MCP_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:30999/mcp"
SESSION_ID = sys.argv[2] if len(sys.argv) > 2 else ""

code = """async (page) => {
  return JSON.stringify({total: 0, posts: [], msg: "hello"});
}"""

body = json.dumps({
    "jsonrpc": "2.0",
    "id": 10,
    "method": "tools/call",
    "params": {
        "name": "browser_run_code_unsafe",
        "arguments": {"code": code}
    }
}).encode('utf-8')

req = urllib.request.Request(
    MCP_URL,
    data=body,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": SESSION_ID
    }
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode('utf-8')
    print("RAW RESPONSE:")
    print(repr(raw))
    print("\n---")
    for line in raw.split('\n'):
        if line.startswith('data: '):
            obj = json.loads(line[6:])
            print("PARSED:", json.dumps(obj, indent=2, ensure_ascii=False)[:500])
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print("Body:", e.read().decode('utf-8')[:500])
