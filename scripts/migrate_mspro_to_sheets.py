#!/usr/bin/env python3
"""Create Ms Pro Google Sheet and migrate xlsx data."""
import json, sys
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Auth
with open("/home/user/.hermes/google_token.json") as f:
    token = json.load(f)
creds = Credentials.from_authorized_user_info(
    token, ["https://www.googleapis.com/auth/spreadsheets"])
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
service = build("sheets", "v4", credentials=creds)
sheet_api = service.spreadsheets()

# Create sheet
r = sheet_api.create(body={"properties": {"title": "Ms Pro 内容日历"}}).execute()
sheet_id = r["spreadsheetId"]
sheet_url = r["spreadsheetUrl"]
print(f"CREATED: {sheet_id}")
print(f"URL: {sheet_url}")

# Rename default sheet from "工作表1" to "内容日历"
service.spreadsheets().batchUpdate(
    spreadsheetId=sheet_id,
    body={"requests": [{"updateSheetProperties": {
        "properties": {"sheetId": 0, "title": "内容日历"},
        "fields": "title"
    }}]}
).execute()
print("Renamed sheet to: 内容日历")

# Data to write
headers = ['#', '周次', '状态', '建议日期', '题材', '标题方向', '内容角度', '主打服务/卖点', '风格', '完整帖文', '备注']
rows = [
    ["1", "May W2 (5/9-15)", "📤 已发布", "5月9日（周六）母亲节", "母亲节专题", "「家是因为有妈妈才叫家」", "品牌温度——借母亲节建立品牌人格，不卖服务，先让人认识 Ms Pro。核心洞察：Ms Pro 管理的是「家」，而家的定义是妈妈。", "品牌形象", "温情叙事", "我们管理很多间房子。\n\n打扫得很干净，布置得很用心，每一间都准备好迎接它的住客。\n\n但不是每一间，都能叫**家**。\n\n家不是四面墙。家是妈妈在厨房切菜的声音，是她一边唠叨一边帮你折衣服的手，是你出门时她站在门口那句「到了记得告诉我」。\n\n有妈妈在的地方，再小的空间也是家。\n\n---\n\n母亲节快乐。\n\n致每一个把房子变成家的妈妈 🤍\n\n---\n\n*Ms Pro Management*\n*守护每一个家的温度。*\n\n---\n\n#母亲节快乐 #HappyMothersDay #MsProManagement #JohorBahru #MountAustin", "路线A · 配图：暖黄民宿客厅，玄关女式拖鞋，不露脸。暖黄+米白色调。· 已发布 5/9"],
    ["2", "May W2 (5/9-15)", "✅ 帖文完成", "5月13日（周三）", "品牌介绍", "「每一间民宿背后，都有一个我们没见过面的业主」", "品牌介绍——Post 1 情感锚点后的价值钩子。从 Ms Pro 视角讲「我们怎么守护家」，核心记忆点：「你不必出现。」传递省心+信任。", "省心托管 / 专业信任", "温情叙事 + 专业", "我们很少见到业主。\n\n大多数时候，我们只见到他们的房子。\n\n钥匙放在信箱，或者在管理处转交。打开门，是另一户人家的生活痕迹——沙发上的靠垫、冰箱里的饮料、阳台晾着的毛巾。\n\n然后我们开始工作。打扫、换床单、检查空调、拍照上传、回复订房信息、处理退房。每一个细节，都当作自己的房子在做。\n\n---\n\n业主在哪里？\n\n可能在 KL 开会，在新加坡上班，在澳洲陪孩子读书。可能根本没来过 Mount Austin，只是多年前买下这间公寓，一直出租。\n\n他们偶尔发 WhatsApp 问一句「这个月怎样？」我们回一句「一切 OK，这是月报。」\n\n然后就没了。没有寒暄，没有多余的对话。\n\n---\n\n我们不认识他们。但我们认真管好他们的房子。\n\n这是专业。也是信任。\n\n---\n\n你不必出现。房子交给我们，就好。\n\n---\n\n*Ms Pro Management —— 守护每一个家的温度。*\n\n📲 WhatsApp: 010-206 5796\n\n---\n\n#MsProManagement #HomestayJB #MountAustin #民宿管理 #JohorBahru", "路线B · 配图英文提示词已附。详细简报见上方。"],
]

# Write header
sheet_api.values().update(
    spreadsheetId=sheet_id,
    range="内容日历!A1:K1",
    body={"values": [headers]},
    valueInputOption="RAW"
).execute()

# Write data
sheet_api.values().update(
    spreadsheetId=sheet_id,
    range=f"内容日历!A2:K{1+len(rows)}",
    body={"values": rows},
    valueInputOption="RAW"
).execute()

# Verify
r = sheet_api.values().get(
    spreadsheetId=sheet_id,
    range="内容日历!A:K"
).execute()
values = r.get("values", [])
print(f"VERIFY: {len(values)} rows (1 header + {len(values)-1} data)")

# Print summary
print(f"\n✅ MIGRATION COMPLETE")
print(f"Sheet ID: {sheet_id}")
print(f"URL: {sheet_url}")
print(f"Rows migrated: {len(rows)}")
