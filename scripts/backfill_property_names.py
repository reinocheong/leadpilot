#!/usr/bin/env python3
"""Backfill property names for rows that were parsed before extraction improvements.

Safe: only updates rows where property name column is empty.
Shows a preview first, use --apply to write.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from auth.lib.sheet_ops import read_sheet, get_sheets_svc
from processors.lib.property_data import normalize_property_name, is_valid_property_name
from processors.lib.extractors import extract_property_name

SHEET_ID = '1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM'
SHEET_NAME = 'JB Rentals'

def main():
    apply = '--apply' in sys.argv
    dry_run = not apply
    
    svc = get_sheets_svc()
    rows = read_sheet(SHEET_ID, f'{SHEET_NAME}!A:L')
    headers = [h.strip().lower() for h in rows[0]]
    
    # Column index: 1 = Property Name, 11 = Post Text
    prop_col = 1   # B
    text_col = 11  # L
    
    updates = []
    for i, row in enumerate(rows[1:], start=2):  # Sheet is 1-indexed, row 1 = header
        current_prop = (row[prop_col] if len(row) > prop_col else '').strip()
        post_text = (row[text_col] if len(row) > text_col else '').strip()
        
        if current_prop or not post_text:
            continue
        
        result = extract_property_name(post_text)
        if result and is_valid_property_name(result):
            updates.append((i, prop_col + 1, result))  # Sheet col is 1-indexed: B = 2
    
    print(f'扫描 {len(rows)-1} 行')
    print(f'可回填楼盘名: {len(updates)} 行')
    print()
    
    # Group by property for preview
    from collections import Counter
    props = Counter(u[2] for u in updates)
    print('=== 回填预览 ===')
    for name, count in props.most_common(20):
        print(f'  {name}: {count}行')
    
    if not updates:
        print('没有需要回填的行')
        return
    
    if dry_run:
        print()
        print('预览模式，未写入。加 --apply 执行回填')
        return
    
    # Apply updates
    batch = []
    for row_num, col, value in updates:
        batch.append({
            'range': f'{SHEET_NAME}!{chr(64+col)}{row_num}',
            'values': [[value]]
        })
    
    # Google Sheets API allows batch updates
    body = {'valueInputOption': 'USER_ENTERED', 'data': batch}
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body=body
    ).execute()
    
    print(f'✅ 已回填 {len(updates)} 行')

if __name__ == '__main__':
    main()
