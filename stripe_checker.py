#!/usr/bin/env python3
"""Stripe Payment Checker — runs periodically, auto-activates subscriptions."""
import os, json, sys
from datetime import datetime, timedelta
import stripe

# Load secrets
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
secrets = {}
with open(ENV_FILE) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            secrets[k.strip()] = v.strip()

stripe.api_key = secrets.get("STRIPE_SECRET_KEY", "")
TRACKING_FILE = "/home/user/leadpilot/processed_payments.txt"
MY_TZ = timedelta(hours=8)

def load_processed():
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE) as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed(session_id):
    with open(TRACKING_FILE, "a") as f:
        f.write(session_id + "\n")

def check_and_activate():
    """Check Stripe for new successful payments, activate subscriptions."""
    processed = load_processed()
    new_payments = []
    
    # Query recent checkout sessions (last 24h)
    sessions = stripe.checkout.Session.list(
        status='complete',
        created={'gte': int((datetime.utcnow() - timedelta(hours=24)).timestamp())},
        limit=50
    )
    
    for session in sessions.auto_paging_iter():
        sid = session.id
        if sid in processed:
            continue
        
        email = session.customer_details.email if session.customer_details else None
        if not email:
            continue
        
        # Determine plan from amount
        amount = session.amount_total / 100
        plan = "standard"  # All our plans are standard now
        days = 30
        
        new_payments.append({
            "session_id": sid,
            "email": email,
            "name": session.customer_details.name or email.split('@')[0],
            "plan": plan,
            "amount": amount,
            "days": days
        })
        
        save_processed(sid)
    
    return new_payments

if __name__ == "__main__":
    payments = check_and_activate()
    if payments:
        for p in payments:
            print(f"💰 {p['name']} ({p['email']}) — RM {p['amount']:.0f} ({p['plan']})")
        # Output JSON for sub_mgr.py to consume
        print("---JSON---")
        print(json.dumps(payments, ensure_ascii=False))
    else:
        print("📭 没有新付款")
