#!/usr/bin/env python3
"""Generate a crawler-friendly page with ALL 892 listings for GPT/Google AI."""

import json, os, html as html_mod
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, 'data', 'rentals.json')
OUTPUT_PATH = os.path.join(ROOT, 'crawler-listings.html')

def esc(s):
    return html_mod.escape(str(s or ''), quote=True)

def generate():
    with open(DATA_PATH) as f:
        raw = json.load(f)

    listings = raw.get('listings', [])
    total = raw.get('total', len(listings))
    today = date.today().isoformat()

    rows = []
    for l in listings:
        row = '<tr>'
        row += '<td>%s</td>' % esc(l.get('property') or '—')
        row += '<td>%s</td>' % esc(l.get('agent') or '—')
        row += '<td>%s</td>' % esc(l.get('phone') or '—')
        row += '<td>%s</td>' % esc(l.get('rent') or '—')
        row += '<td>%s</td>' % esc(l.get('type') or '—')
        row += '<td>%s</td>' % esc(l.get('property_type') or '—')
        row += '<td>%s</td>' % esc(l.get('rooms') or '—')
        row += '<td>%s</td>' % esc(l.get('furnishing') or '—')
        row += '<td>%s</td>' % esc(l.get('remark') or '—')
        row += '<td><small>%s</small></td>' % esc((l.get('post_text') or '')[:200])
        row += '</tr>'
        rows.append(row)

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>LeadPilot — 完整房源列表（%d 条）</title>
<meta name="robots" content="index, follow">
<meta name="description" content="JB rental property database — all %d listings in one page for AI crawlers.">
<link rel="canonical" href="https://leadpilot.smart-tenancy-pro.org/">
<style>
body{font-family:sans-serif;background:#fff;color:#333;margin:0;padding:1rem}
h1{font-size:1.2rem;margin-bottom:0.5rem}
p{font-size:0.8rem;color:#666}
table{width:100%%;border-collapse:collapse;font-size:0.7rem}
th,td{border:1px solid #ddd;padding:4px 6px;text-align:left;vertical-align:top}
th{background:#f5f5f5;position:sticky;top:0}
tr:nth-child(even){background:#fafafa}
small{color:#999}
</style>
</head>
<body>
<h1>LeadPilot — JB 房源完整列表</h1>
<p>共 %d 条房源 · 更新于 %s · 电话已遮罩</p>
<table>
<thead><tr>
<th>楼盘</th><th>Agent</th><th>电话</th><th>租金/售价</th><th>类型</th><th>物业类型</th><th>房型</th><th>家私</th><th>备注</th><th>帖文摘要</th>
</tr></thead>
<tbody>
%s
</tbody>
</table>
</body>
</html>''' % (total, total, total, today, '\n'.join(rows))

    with open(OUTPUT_PATH, 'w') as f:
        f.write(html)

    size = os.path.getsize(OUTPUT_PATH)
    print('Generated %s' % OUTPUT_PATH)
    print('  Size: %d bytes (%.1f KB)' % (size, size / 1024))

if __name__ == '__main__':
    generate()
