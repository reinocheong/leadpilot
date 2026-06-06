#!/usr/bin/env python3
"""
Local export — generates rentals.json from parsed local JSON.
No Google Sheets dependency.
"""
import json, os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from collections import Counter

MY_TZ = ZoneInfo("Asia/Kuala_Lumpur")
PARSED_JSON = "/home/user/fb_data/fb_posts_parsed.json"
OUT_DIR = "/home/user/leadpilot/data"
OUT_PATH = os.path.join(OUT_DIR, "rentals.json")

def mask_phone(phone: str) -> str:
    p = phone.strip()
    if not p: return ""
    if p.startswith("+"):
        digits = p[1:]; prefix = "+"
    else:
        digits = p; prefix = ""
    if len(digits) < 7: return p
    return f"{prefix}{digits[:4]}***{digits[-3:]}"

def parse_rent(rent_str: str) -> str:
    if not rent_str: return ""
    r = rent_str.strip().lower().replace("rm", "").replace(".00", "").strip()
    return r

def main():
    now = datetime.now(MY_TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if not os.path.exists(PARSED_JSON):
        print(f"❌ {PARSED_JSON} 不存在")
        return

    with open(PARSED_JSON, "r") as f:
        all_parsed = json.load(f)

    listings = []
    today_new = 0
    prop_counter = Counter()

    for row in all_parsed:
        phone = str(row.get("phone", "")).strip()
        if not phone or len(phone) < 7:
            continue

        scraped = str(row.get("scraped_at", "")).strip()
        try:
            scraped_dt = datetime.fromisoformat(scraped)
            if scraped_dt >= today_start:
                today_new += 1
        except:
            pass

        prop = row.get("property", "").strip()
        if prop:
            prop_counter[prop] += 1

        rent_raw = str(row.get("rent", "")).strip()
        rent = parse_rent(rent_raw)
        if rent:
            try:
                rent = f"{int(rent):,}"
            except:
                pass

        listings.append({
            "agent": row.get("agent", "").strip(),
            "property": prop,
            "type": row.get("listing_type", "").strip(),
            "property_type": row.get("type", "").strip(),
            "rooms": row.get("rooms", "").strip(),
            "furnishing": row.get("furnishing", "").strip(),
            "rent": rent,
            "phone": phone,
            "link": row.get("link", "").strip(),
            "remark": row.get("remark", "").strip(),
            "scraped_at": scraped,
            "post_text": row.get("post_text", "").strip(),
        })

    listings.sort(key=lambda x: x["scraped_at"], reverse=True)
    top_props = [p for p, _ in prop_counter.most_common(10)]

    output = {
        "updated_at": now.isoformat(),
        "total": len(listings),
        "today_new": today_new,
        "top_properties": top_props,
        "listings": listings,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 导出完成: {len(listings)} 条 ({today_new} 今日新), top: {top_props[:5]}")
    print(f"   → {OUT_PATH}")

if __name__ == "__main__":
    main()
