#!/usr/bin/env python3
"""Re-extract phone numbers from post_text and update Google Sheets + rentals.json."""
import json, re, os, sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SA_KEY = '/home/user/.hermes/google_sa_rental.json'
SHEET_ID = '1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM'
PROJECT_ROOT = '/home/user/leadpilot'

def normalize_phone(raw: str) -> str:
    if not raw or not raw.strip():
        return ''
    if '*' in raw:
        return ''
    digits = re.sub(r'\D', '', raw)
    if len(digits) < 8 or len(digits) > 15:
        return ''
    if raw.startswith('+'):
        if digits.startswith('60') and 10 <= len(digits) <= 13:
            return '+' + digits
        if digits.startswith('65') and 10 <= len(digits) <= 12:
            return '+' + digits
        return ''
    if re.match(r'^01\d', raw) and 10 <= len(digits) <= 11:
        return '+60' + digits[1:]
    if digits.startswith('60') and 10 <= len(digits) <= 13:
        return '+' + digits
    if re.match(r'^[89]\d{7}$', digits):
        return '+65' + digits
    return ''

def extract_phone_from_text(text: str) -> str:
    if not text:
        return ''
    patterns = [
        r'(\+?6?0[1-9][0-9])[\s\-]?([0-9]{3,4})[\s\-]?([0-9]{4})',
        r'(\+?65)[\s\-]?([0-9]{4})[\s\-]?([0-9]{4})',
        r'\b(01[0-9])[\s\-]?([0-9]{3,4})[\s\-]?([0-9]{4})\b',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            raw = ''.join(m.groups())
            norm = normalize_phone(raw)
            if norm:
                return norm
    return ''

def main():
    dry_run = '--apply' not in sys.argv
    
    # Read current rentals.json
    with open(os.path.join(PROJECT_ROOT, 'data', 'rentals.json')) as f:
        cur = json.load(f)
    
    listings = cur.get('listings', [])
    print(f'Current listings: {len(listings)}')
    
    # Try to fix phones from post_text
    fixes = []
    for i, l in enumerate(listings):
        current_phone = l.get('phone', '')
        if not current_phone or '*' in current_phone:
            # Try to extract from post_text
            new_phone = extract_phone_from_text(l.get('post_text', ''))
            if new_phone and new_phone != current_phone:
                fixes.append((i, l.get('agent', ''), current_phone, new_phone, l.get('link', '')))
    
    print(f'Can fix {len(fixes)} phone numbers from post_text')
    
    if dry_run:
        print('\n=== DRY RUN — 预览 ===')
        for idx, agent, old, new, link in fixes[:30]:
            print(f'  #{idx} [{agent}] {old} → {new}')
        if len(fixes) > 30:
            print(f'  ...还有 {len(fixes)-30} 条')
        print(f'\n确认无误: python3 scripts/fix_phones.py --apply')
        return
    
    # Apply: update rentals.json
    for idx, agent, old, new, link in fixes:
        listings[idx]['phone'] = new
    
    cur['listings'] = listings
    cur['total'] = len(listings)
    
    with open(os.path.join(PROJECT_ROOT, 'data', 'rentals.json'), 'w', encoding='utf-8') as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
    
    print(f'✅ Updated rentals.json: {len(fixes)} phones fixed')
    
    # Also update Google Sheets
    creds = Credentials.from_service_account_file(SA_KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    svc = build('sheets', 'v4', credentials=creds)
    
    # Read sheet to get current state
    resp = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range='JB Rentals!A:H').execute()
    rows = resp.get('values', [])
    
    # Build link → row mapping (H=phone col index 7)
    link_to_row = {}
    for i, row in enumerate(rows[1:], start=2):  # 1-based row number, skip header
        if len(row) > 8:
            link = row[8].strip()
            if link:
                link_to_row[link] = i
    
    # Build sheet updates
    requests = []
    updated = 0
    not_found = 0
    for idx, agent, old, new, link in fixes:
        if link in link_to_row:
            row_num = link_to_row[link]
            requests.append({
                'updateCells': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row_num - 1,
                        'endRowIndex': row_num,
                        'startColumnIndex': 7,
                        'endColumnIndex': 8
                    },
                    'rows': [{'values': [{'userEnteredValue': {'stringValue': new}}]}],
                    'fields': 'userEnteredValue'
                }
            })
            updated += 1
        else:
            not_found += 1
    
    # Send in batches
    if requests:
        for batch_start in range(0, len(requests), 50):
            batch = requests[batch_start:batch_start + 50]
            svc.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={'requests': batch}
            ).execute()
            print(f'  Sheet更新 {batch_start + len(batch)}/{len(requests)}')
    
    print(f'\n✅ Sheets更新: {updated} 条, 未匹配: {not_found}')
    print(f'总计修复: {len(fixes)} 个电话')

if __name__ == '__main__':
    main()
