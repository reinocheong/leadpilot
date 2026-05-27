#!/usr/bin/env python3
import json, hashlib, secrets, os, sys, urllib.request
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Import sheet ops - works whether run as python3 auth_server.py or from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from auth.lib.sheet_ops import read_sheet, append_row, get_sheets_svc

INTERNAL_SHEET_ID = '1gCynpcBHYgoGiRkfVOJOCOjtiOIl0NuGgpyEexAF3W4'
RENTALS_SHEET_ID  = '1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM'
SUB_SHEET_ID      = '1zLOyuRbZnycvD0tc4UPLSoR3mfClwkiDOPw3W-v-gXg'
GOOGLE_CLIENT_ID  = '788231638010-v1k56qso1brtia2u9ddqghbbpes4pkm9.apps.googleusercontent.com'
TOKEN_TTL_HOURS, TRIAL_DAYS, PORT = 24, 3, int(os.environ.get('PORT', 8777))

def log_msg(msg): sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

def sha256(s): return hashlib.sha256(s.encode()).hexdigest()
def gen_token(): return secrets.token_urlsafe(36)

# ── Session 存储（内存，重启后失效——token 24h 内有效）──
sessions = {}  # token -> {"email": ..., "name": ..., "expires": ...}

def find_user(email):
    rows = read_sheet(INTERNAL_SHEET_ID, '授权用户!A:F')
    for i, row in enumerate(rows[1:], start=1):
        if len(row) >= 5 and (row[0] or '').strip().lower() == email.strip().lower():
            return row, i
    return None, -1

def check_subscription(email):
    """Check subscription Sheet for status."""
    rows = read_sheet(SUB_SHEET_ID, '订阅状态!A:G')
    for row in rows[1:]:
        if len(row) >= 7 and (row[1] or '').strip().lower() == email.strip().lower():
            status = row[6].strip()
            end_date = row[5].strip() if len(row) > 5 else ''
            return status, end_date
    return None, None

def verify_google_token(id_token):
    """Verify Google ID token via Google's tokeninfo endpoint."""
    url = f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get('aud') != GOOGLE_CLIENT_ID:
            return None, 'Client ID 不匹配'
        return data, None
    except Exception as e:
        return None, str(e)

def create_session(email, name):
    token = gen_token()
    expires = datetime.now() + timedelta(hours=TOKEN_TTL_HOURS)
    sessions[token] = {"email": email, "name": name, "expires": expires.isoformat()}
    return token

def validate_session(token):
    if token in sessions:
        s = sessions[token]
        if datetime.fromisoformat(s["expires"]) > datetime.now():
            return s
        else:
            del sessions[token]
    return None

def get_rentals_data():
    rows = read_sheet(RENTALS_SHEET_ID, 'JB Rentals!A:L')
    if len(rows) < 2: return {'error': '暂无数据'}
    headers = [h.strip().lower() for h in rows[0]]
    listings = []
    for row in rows[1:]:
        d = dict(zip(headers, row + ['']*(len(headers)-len(row))))
        if not d.get('phone'): continue
        listings.append({
            'agent': d.get('agent name'),
            'property': d.get('property name'),
            'rent': d.get('rent (rm)'),
            'phone': d.get('phone'),
            'link': d.get('link'),
            'property_type': d.get('property type'),
            'type': d.get('listing type'),
            'furnishing': d.get('furnishing'),
            'rooms': d.get('rooms'),
            'remark': d.get('remark'),
            'post_text': d.get('post text'),
            'scraped_at': d.get('scraped at')
        })
    # Sort by scraped_at descending (newest first)
    from collections import Counter
    listings.sort(key=lambda l: l.get('scraped_at') or '', reverse=True)
    props = [l.get('property') for l in listings if l.get('property')]
    top = [p for p, _ in Counter(props).most_common(15)]
    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')
    return {
        'updated_at': now,
        'total': len(listings),
        'today_new': 0,
        'top_properties': top,
        'listings': listings
    }

def mask_phone_in_text(text):
    """Mask Malaysian phone numbers in arbitrary text content."""
    if not text:
        return text
    import re
    # Match: +60123456789, 0123456789, 60123456789, 012-3456789, +6012-3456789 etc.
    # Also handle: +60 12-345 6789, 012 345 6789
    pattern = r'(\+?6?0[1-9][0-9]?)[\s\-]?([0-9]{3,4})[\s\-]?([0-9]{4})'
    def repl(m):
        prefix = m.group(1)  # e.g., +6012, 012, 012
        return prefix + '*******'
    return re.sub(pattern, repl, text)

def mask_phone(phone):
    """Mask phone number — show first 5 chars + asterisks."""
    if not phone:
        return None
    p = phone.strip()
    if len(p) <= 5:
        return p + '****'
    return p[:5] + '****'

def get_preview_data():
    """Return ALL listings for unauthenticated preview, with masked phone numbers."""
    rows = read_sheet(RENTALS_SHEET_ID, 'JB Rentals!A:L')
    if len(rows) < 2:
        return {'preview': True, 'total': 0, 'listings': [], 'top_properties': []}
    headers = [h.strip().lower() for h in rows[0]]
    all_listings = []
    for row in rows[1:]:
        d = dict(zip(headers, row + ['']*(len(headers)-len(row))))
        phone = d.get('phone', '').strip()
        prop = (d.get('property name') or '').strip()
        agent = (d.get('agent name') or '').strip()
        scraped = (d.get('scraped at') or '').strip()
        if not phone: continue
        entry = {
            'agent': agent or None,
            'property': prop or None,
            'rent': d.get('rent (rm)'),
            'phone': mask_phone(phone),
            'link': d.get('link'),
            'property_type': d.get('property type'),
            'type': d.get('listing type'),
            'furnishing': d.get('furnishing'),
            'rooms': d.get('rooms'),
            'remark': d.get('remark'),
            'post_text': mask_phone_in_text(d.get('post text')),
            'scraped_at': scraped or None
        }
        all_listings.append(entry)
    from collections import Counter
    props = [l.get('property') for l in all_listings if l.get('property')]
    top = [p for p, _ in Counter(props).most_common(15)]
    def sort_key(e):
        ts = e.get('scraped_at') or ''
        return ts
    all_listings.sort(key=sort_key, reverse=True)
    return {
        'preview': True,
        'total': len(all_listings),
        'listings': all_listings,
        'top_properties': top
    }

class AuthHandler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == '/health':
            self._json({'ok': True})

        elif path == '/preview':
            data = get_preview_data()
            self._json(data)

        elif path == '/data':
            token = params.get('token', [None])[0]
            session = validate_session(token)
            if not session:
                self._json({'error': '未登录或会话已过期'}, 401)
                return

            # Get subscription status
            _, status = find_user(session['email'])
            sub_status, end_date = check_subscription(session['email'])

            # Check if expired
            is_expired = False
            if sub_status in ('expired', '🔴 已过期'):
                is_expired = True
            elif end_date:
                try:
                    if datetime.strptime(end_date[:10], '%Y-%m-%d') < datetime.now():
                        is_expired = True
                except:
                    pass

            data = get_rentals_data()
            data['session'] = {
                'name': session['name'],
                'email': session['email'],
                'status': 'expired' if is_expired else 'active'
            }
            self._json(data)

        else:
            self._json({'error': 'Not found'}, 404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

        if self.path == '/google-auth':
            id_token = body.get('google_token', '')
            info, error = verify_google_token(id_token)
            if error:
                self._json({'error': f'Google 验证失败: {error}'}, 401)
                return

            email = info.get('email', '').lower()
            name = info.get('name', email.split('@')[0])

            row, _ = find_user(email)
            if row:
                # Existing user — check status/expiry
                sub_status, end_date = check_subscription(email)
                is_expired = False
                if sub_status in ('expired', '🔴 已过期'):
                    is_expired = True
                elif end_date:
                    try:
                        if datetime.strptime(end_date[:10], '%Y-%m-%d') < datetime.now():
                            is_expired = True
                    except:
                        pass
                token = create_session(email, row[2] if len(row) > 2 else name)
                log_msg(f"Google 登录成功: {email}")
                self._json({
                    'token': token,
                    'name': row[2] if len(row) > 2 else name,
                    'status': 'expired' if is_expired else 'active'
                })
            else:
                # New user — auto create 3-day trial
                now = datetime.now()
                expiry = (now + timedelta(days=TRIAL_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
                # Add to 授权用户 Sheet
                append_row(INTERNAL_SHEET_ID, '授权用户!A:F',
                    [email, 'google', name, expiry, 'active', 'Google 自动开通试用'])
                # Also add to 订阅状态 Sheet
                append_row(SUB_SHEET_ID, '订阅状态!A:G',
                    [name, email, '', 'trial', now.strftime('%Y-%m-%d %H:%M'), expiry, '🟡 试用中'])
                token = create_session(email, name)
                log_msg(f"Google 新用户自动开通: {email}")
                self._json({
                    'token': token,
                    'name': name,
                    'status': 'trial',
                    'is_new': True
                })

        else:
            self._json({'error': 'Not found'}, 404)

def main():
    server = HTTPServer(('0.0.0.0', PORT), AuthHandler)
    log_msg(f"Auth server running on {PORT}")
    server.serve_forever()

if __name__ == '__main__':
    main()
