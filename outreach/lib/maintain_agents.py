#!/usr/bin/env python3
import sys, os, time
sys.path.insert(0, "/home/user/leadpilot")

from outreach.lib.sheet_reader import get_agents_from_sheet
from outreach.lib.dedup_utils import dedup_agents
from outreach.lib.sheet_reader import get_sheets_service
from googleapiclient.errors import HttpError

INTERNAL_SHEET_ID = "1gCynpcBHYgoGiRkfVOJOCOjtiOIl0NuGgpyEexAF3W4"

def update_with_retry(svc, spreadsheet_id, range_name, body, max_retries=3):
    """Google Sheets API update with retry on 5xx errors."""
    for attempt in range(max_retries):
        try:
            return svc.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=range_name,
                valueInputOption="RAW", body=body
            ).execute()
        except HttpError as e:
            if e.resp.status >= 500 and attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"⚠️ Google API 503, {wait}s 后重试 ({attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue
            raise

def main():
    print("[outreach/lib/maintain_agents.py] 开始维护 Agent List")
    raw_agents = get_agents_from_sheet()
    unique_agents = dedup_agents(raw_agents)
    
    # Update Agent List tab with retry
    svc = get_sheets_service()
    rows = [["Phone", "Agent", "Status"]] + [[a['phone'], a['agent'], 'active'] for a in unique_agents]
    update_with_retry(svc, INTERNAL_SHEET_ID, "Agent List!A:C", {"values": rows})
    print(f"✅ 维护完成: {len(unique_agents)} 个唯一 Agent")

if __name__ == "__main__": main()
