#!/usr/bin/env python3
"""Smart Tenancy Pro — 每4小时运行状态汇总"""
import subprocess, json, os, sqlite3
from datetime import datetime, timezone, timedelta

MYT = timezone(timedelta(hours=8))
now = datetime.now(MYT)
today = now.strftime("%Y-%m-%d")
hour = now.hour

PROJECT = "/home/user/jb-rental-intel"
DATA_DIR = "/home/user/fb_data"
DB_PATH = os.path.join(PROJECT, "subscribers.db")

lines = []
lines.append(f"📊 Smart Tenancy Pro · {now.strftime('%H:%M')} 快报")
lines.append("")

# 1. FB 爬虫统计
json_path = os.path.join(DATA_DIR, "fb_posts_raw.json")
total_posts = 0
if os.path.exists(json_path):
    with open(json_path) as f:
        data = json.load(f)
        total_posts = len(data)
lines.append(f"📌 房源数据库总计: {total_posts} 条")

# 2. 订阅统计
trial = active = expired = 0
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT status, COUNT(*) FROM subscribers GROUP BY status")
        for row in c.fetchall():
            if row[0] == "trial": trial = row[1]
            elif row[0] == "active": active = row[1]
            elif row[0] == "expired": expired = row[1]
    except: pass
    conn.close()

parts = []
if trial: parts.append(f"试用 {trial}")
if active: parts.append(f"付费 {active}")
if expired: parts.append(f"过期 {expired}")
sub_info = " · ".join(parts) if parts else "暂无订户"
lines.append(f"👥 订阅: {sub_info}")

# 3. Agent List 统计（从内部 Sheet 读取）
agent_count = 0
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_service_account_file(
        '/home/user/.hermes/google_sa_rental.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    svc = build('sheets', 'v4', credentials=creds)
    r = svc.spreadsheets().values().get(
        spreadsheetId='1gCynpcBHYgoGiRkfVOJOCOjtiOIl0NuGgpyEexAF3W4',
        range='Agent List!A:F'
    ).execute()
    vals = r.get('values', [])
    if vals and len(vals) >= 2:
        agent_count = sum(1 for row in vals[1:] if row and row[0].strip())
except Exception:
    pass
lines.append(f"📋 Agent List: {agent_count} 人（去重）")

print("\n".join(lines))
