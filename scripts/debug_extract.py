#!/usr/bin/env python3
"""Debug MCP response - check exact text format."""
import json, re, urllib.request

MCP_URL = "http://127.0.0.1:30999/mcp"

body0 = json.dumps({
    "jsonrpc":"2.0","id":1,"method":"initialize",
    "params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"debug","version":"1.0"}}
}).encode('utf-8')
req0 = urllib.request.Request(MCP_URL, data=body0, headers={
    "Content-Type":"application/json","Accept":"application/json, text/event-stream"
})
with urllib.request.urlopen(req0, timeout=30) as resp:
    sid = resp.headers.get('mcp-session-id','')
    resp.read()

code = """async (page) => { return JSON.stringify({total:0,posts:[]}); }"""
body = json.dumps({
    "jsonrpc":"2.0","id":10,"method":"tools/call",
    "params":{"name":"browser_run_code_unsafe","arguments":{"code":code}}
}).encode('utf-8')
req = urllib.request.Request(MCP_URL, data=body, headers={
    "Content-Type":"application/json","Accept":"application/json, text/event-stream","Mcp-Session-Id":sid
})
with urllib.request.urlopen(req, timeout=120) as resp:
    raw = resp.read().decode('utf-8')

for line in raw.split('\n'):
    line = line.strip()
    if line.startswith('data: '):
        obj = json.loads(line[6:])
        text = obj['result']['content'][0]['text']
        print("=== Python repr of text ===")
        print(repr(text))
        print("\n=== Hex dump of first 200 chars ===")
        for i, c in enumerate(text[:200]):
            if i % 50 == 0:
                print(f"\n{i:4d}: ", end='')
            print(f"{ord(c):02x} ", end='')
        print()
        
        # Now try extraction
        parts = text.split('### Result')
        if len(parts) >= 2:
            after = parts[1]
            print(f"\n=== after '### Result' (repr) ===")
            print(repr(after))
            result_section = after.split('###')[0].strip()
            print(f"\n=== result_section after strip (repr) ===")
            print(repr(result_section))
            
            # Check if wrapped in \"...\" 
            if result_section.startswith('\\"') and result_section.endswith('\\"'):
                result_section = result_section[2:-2]
                print(f"\n=== after removing outer \\\" (repr) ===")
                print(repr(result_section))
            elif result_section.startswith('"') and result_section.endswith('"'):
                result_section = result_section[1:-1]
                print(f"\n=== after removing outer \" (repr) ===")
                print(repr(result_section))

            # Try to parse as JSON
            try:
                data = json.loads(result_section)
                print(f"\n=== JSON parsed OK ===")
                print(f"total={data.get('total')}, posts={len(data.get('posts',[]))}")
            except Exception as e:
                print(f"\n=== JSON parse error: {e} ===")
