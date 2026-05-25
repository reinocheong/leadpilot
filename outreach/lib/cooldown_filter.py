#!/usr/bin/env python3
"""
Cooldown Filter — decide which agents to contact today.
Filters out: already contacted within 30 days, already subscribed.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Set, Optional

MY_TZ = ZoneInfo("Asia/Kuala_Lumpur")
COOLDOWN_DAYS = 30
DAILY_LIMIT = 20  # fallback default


def filter_candidates(
    agents: List[Dict],
    outreach_records: List[Dict],
    subscribed_phones: Set[str] = None,
    limit: int = DAILY_LIMIT,
    cooldown_days: int = COOLDOWN_DAYS,
) -> List[Dict]:
    """Filter agent list down to today's outreach candidates.
    
    Args:
        agents: List of {agent, phone, property, ...} from JB Rentals Sheet
        outreach_records: List of {phone, sent_at, status, ...} from 推广记录 Sheet
        subscribed_phones: Set of phone numbers already on trial/active subscription
        limit: Max candidates per day (default 5)
        cooldown_days: Days before same phone can be contacted again (default 30)
    
    Returns:
        List of candidate agents (up to `limit`)
    """
    now = datetime.now(MY_TZ)
    cutoff = now - timedelta(days=cooldown_days)
    if subscribed_phones is None:
        subscribed_phones = set()
    
    # Build set of phones that are in cooldown or subscribed
    excluded_phones = set()
    for rec in outreach_records:
        phone = str(rec.get("phone", "")).strip().replace(" ", "").replace("-", "")
        if not phone:
            continue
        sent_at_str = rec.get("sent_at", "")
        if sent_at_str:
            try:
                sent_at = datetime.fromisoformat(sent_at_str)
                if sent_at >= cutoff:
                    excluded_phones.add(phone)
            except (ValueError, TypeError):
                pass
        # Also exclude if status is already 已回复/已注册/已付费
        status = rec.get("status", "")
        if status in ("已回复", "已注册", "已付费"):
            excluded_phones.add(phone)
    
    excluded_phones.update(subscribed_phones)
    
    candidates = []
    skipped_cooldown = 0
    skipped_subscribed = 0
    skipped_no_phone = 0
    
    for agent in agents:
        phone = str(agent.get("phone", "")).strip().replace(" ", "").replace("-", "")
        if not phone or len(phone) < 8:
            skipped_no_phone += 1
            continue
        if phone in excluded_phones:
            skipped_cooldown += 1
            continue
        candidates.append({
            "agent": agent.get("agent", ""),
            "phone": phone,
            "property": agent.get("property", ""),
        })
    
    # Pick top N (newest first from how Sheets is sorted)
    selected = candidates[:limit]
    
    print(f"  📊 候选人: {len(candidates)} | 冷却跳过: {skipped_cooldown} | 无电话: {skipped_no_phone}")
    print(f"  🎯 今日选用: {len(selected)}/{limit}")
    
    return selected
