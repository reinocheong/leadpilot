#!/usr/bin/env python3
"""Simplified auth server — serves data publicly, no login/payment."""
import json, os, sys, time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from auth.lib.sheet_ops import read_sheet

PORT = int(os.environ.get('PORT', 8777))

def log_msg(msg): sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

# Preview cache
preview_cache = {"data": None, "ts": 0}
PREVIEW_CACHE_TTL = 1800  # 30 min

def get_preview_cached():
    now = time.time()
    if now - preview_cache["ts"] < PREVIEW_CACHE_TTL and preview_cache["data"] is not None:
        return preview_cache["data"]
    data = get_preview_data()
    preview_cache["data"] = data
    preview_cache["ts"] = now
    return data

def paginate_listings(listings, limit=50, offset=0):
    total = len(listings)
    page = listings[offset:offset + limit]
    has_more = (offset + limit) < total
    next_off = offset + limit if has_more else None
    return {
        'listings': page, 'total': total,
        'has_more': has_more,
        'pagination': {'limit': limit, 'offset': offset, 'next_offset': next_off}
    }

def get_preview_data():
    """Return ALL listings with full phone numbers (no masking)."""
    local_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'rentals.json')
    try:
        with open(local_path) as f:
            cached = json.load(f)
        listings = cached.get('listings', [])
        return {
            'updated_at': cached.get('updated_at'),
            'total': cached.get('total', len(listings)),
            'today_new': cached.get('today_new', 0),
            'top_properties': cached.get('top_properties', []),
            'listings': [{
                'agent': l.get('agent'), 'property': l.get('property'),
                'rent': l.get('rent'), 'phone': l.get('phone'),
                'link': l.get('link'), 'property_type': l.get('property_type'),
                'type': l.get('type'), 'furnishing': l.get('furnishing'),
                'rooms': l.get('rooms'), 'remark': l.get('remark'),
                'post_text': (l.get('post_text') or '')[:500],
                'scraped_at': l.get('scraped_at'),
            } for l in listings],
        }
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    # Fallback: Google Sheets
    rows = read_sheet('1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM', 'JB Rentals!A:L')
    if len(rows) < 2:
        return {'total': 0, 'listings': [], 'top_properties': []}
    headers = [h.strip().lower() for h in rows[0]]
    all_listings = []
    for row in rows[1:]:
        d = dict(zip(headers, row + ['']*(len(headers)-len(row))))
        phone = d.get('phone', '').strip()
        if not phone:
            continue
        all_listings.append({
            'agent': d.get('agent name'), 'property': d.get('property name'),
            'rent': d.get('rent (rm)'), 'phone': phone,
            'link': d.get('link'), 'property_type': d.get('property type'),
            'type': d.get('listing type'), 'furnishing': d.get('furnishing'),
            'rooms': d.get('rooms'), 'remark': d.get('remark'),
            'post_text': (d.get('post text') or '')[:500],
            'scraped_at': d.get('scraped at'),
        })
    from collections import Counter
    props = [l.get('property') for l in all_listings if l.get('property')]
    top = [p for p, _ in Counter(props).most_common(15)]
    all_listings.sort(key=lambda e: e.get('scraped_at') or '', reverse=True)
    return {'total': len(all_listings), 'listings': all_listings, 'top_properties': top}

class Handler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        accept_gzip = self.headers.get('Accept-Encoding', '')
        if 'gzip' in accept_gzip and len(body) > 4096:
            import gzip
            compressed = gzip.compress(body)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(compressed)
        else:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == '/health':
            self._json({'ok': True})

        elif path == '/preview':
            data = get_preview_cached()
            limit = min(int(params.get('limit', [50])[0]), 200)
            offset = int(params.get('offset', [0])[0])
            result = paginate_listings(data.get('listings', []), limit, offset)
            result['updated_at'] = data.get('updated_at')
            result['top_properties'] = data.get('top_properties', [])
            self._json(result)

        elif path == '/preview/search':
            data = get_preview_cached()
            q = params.get('q', [''])[0].lower().strip()
            limit = min(int(params.get('limit', [50])[0]), 200)
            offset = int(params.get('offset', [0])[0])
            if q:
                items = data.get('listings', [])
                q_parts = q.split()
                filtered = [l for l in items if all(
                    p in '|'.join(str(v or '') for v in l.values()).lower()
                    for p in q_parts
                )]
                result = paginate_listings(filtered, limit, offset)
            else:
                result = paginate_listings(data.get('listings', []), limit, offset)
            result['top_properties'] = data.get('top_properties', [])
            self._json(result)

        elif path == '/':
            index_path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
            if os.path.exists(index_path):
                with open(index_path, 'rb') as f:
                    html = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(html)
            else:
                self._json({'error': 'Not found'}, 500)
        else:
            self._json({'error': 'Not found'}, 404)

def main():
    while True:
        try:
            server = HTTPServer(('0.0.0.0', PORT), Handler)
            server.timeout = 60
            log_msg(f"Running on {PORT}")
            server.serve_forever()
        except KeyboardInterrupt:
            log_msg("Stopped")
            break
        except Exception as e:
            log_msg(f"Crashed: {e}, restart in 3s...")
            time.sleep(3)

if __name__ == '__main__':
    main()
