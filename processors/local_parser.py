#!/usr/bin/env python3
"""
Local fallback parser — same logic as fb_parser.py but saves to local JSON.
No Google Sheets dependency.
"""
import json, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.phone_utils import normalize_phone
from lib.text_cleaner import clean_post_text
from lib.filters import is_comment_thread, is_rental_post, is_looking_for_rental
from lib.property_data import is_valid_property_name
from lib.extractors import (
    extract_listing_type, extract_property_name, extract_property_type,
    extract_rooms, extract_rent, extract_furnishing, extract_remark, format_scraped_at
)

RAW_JSON = "/home/user/fb_data/fb_posts_raw.json"
OUT_JSON = "/home/user/fb_data/fb_posts_parsed.json"

def parse_post(post):
    raw_text = post.get("text", "")
    text = clean_post_text(raw_text)
    agent = post.get("agent_name", "")
    phone = normalize_phone(post.get("phone", ""))
    link = post.get("link", "")
    scraped_at = post.get("scraped_at", "")
    group_name = post.get("group_name", "")

    _fb_name = re.compile(r'^[A-Z][a-z]{3,}[A-Z][a-z]{3,}\d*$')
    if not agent or _fb_name.match(agent):
        m = re.match(r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)', text)
        if m and not _fb_name.match(m.group(1)): agent = m.group(1)
        else:
            m = re.match(r'^([\u4e00-\u9fff]{2,4})', text)
            if m: agent = m.group(1)
        if agent and _fb_name.match(agent): agent = ''

    prop_name = extract_property_name(text)
    if prop_name and not is_valid_property_name(prop_name): prop_name = ""
    listing_type = extract_listing_type(text)
    prop_type = extract_property_type(text)
    rooms = extract_rooms(text)
    furnishing = extract_furnishing(text)

    rent = ""
    price_remark = ""
    if listing_type == "出租":
        rent = extract_rent(raw_text) or extract_rent(text)
    else:
        m = re.search(r'(?:RM|rm)\s*(\d[\d,.]{2,6})', raw_text)
        if m:
            try:
                price_remark = f"售价: RM{int(m.group(1).replace(',','')):,}"
            except:
                price_remark = f"售价: RM{m.group(1)}"

    remark = extract_remark(text, prop_name, prop_type, rooms)
    if price_remark:
        remark = f"{price_remark}; {remark}" if remark else price_remark
    if group_name and group_name not in remark:
        remark = f"[{group_name}] {remark}".strip()

    return {
        "agent": agent, "property": prop_name, "listing_type": listing_type,
        "type": prop_type, "rooms": rooms, "furnishing": furnishing,
        "rent": rent, "phone": phone, "link": link, "remark": remark,
        "scraped_at": format_scraped_at(scraped_at), "post_text": text
    }

def main():
    print("[local_parser][main] 开始")
    if not os.path.exists(RAW_JSON):
        print(f"[local_parser][error] {RAW_JSON} 不存在")
        sys.exit(1)

    with open(RAW_JSON, "r") as f:
        raw_posts = json.load(f)
    print(f"[local_parser][processing] 加载了 {len(raw_posts)} 条原始数据")

    parsed, seen, skipped = [], set(), {"comment_thread": 0, "non_rental": 0, "looking": 0}
    for post in raw_posts:
        raw_text = post.get("text", "")
        cleaned = clean_post_text(raw_text)
        if is_looking_for_rental(cleaned) or is_looking_for_rental(raw_text):
            skipped["looking"] += 1; continue
        if not is_rental_post(raw_text):
            skipped["non_rental"] += 1; continue
        if is_comment_thread(raw_text):
            skipped["comment_thread"] += 1; continue
        row = parse_post(post)
        if row["link"] in seen: continue
        seen.add(row["link"]); parsed.append(row)

    print(f"[local_parser][processing] 解析完成: {len(parsed)} 条去重后")

    # Load existing parsed data for dedup
    existing_links = set()
    if os.path.exists(OUT_JSON):
        with open(OUT_JSON, "r") as f:
            existing = json.load(f)
        for p in existing:
            if p.get("link"):
                existing_links.add(p["link"])
        print(f"[local_parser][dedup] 已有 {len(existing)} 条历史数据")

    unique_new = [p for p in parsed if p["link"] not in existing_links]
    print(f"[local_parser][dedup] 新增 {len(unique_new)} 条")

    # Merge and save
    all_parsed = unique_new[:]
    if os.path.exists(OUT_JSON):
        with open(OUT_JSON, "r") as f:
            all_parsed = json.load(f) + unique_new

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_parsed, f, ensure_ascii=False, indent=2)

    print(f"[local_parser][main] 结束: 总计 {len(all_parsed)} 条, 本次新增 {len(unique_new)} 条")
    print(json.dumps({
        "total": len(all_parsed), "new": len(unique_new),
        "crawled": len(raw_posts), "skipped": skipped
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
