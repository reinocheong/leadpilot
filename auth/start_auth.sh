#!/bin/bash
# Start JB Rentals Auth services with Cloudflare Tunnel

LOG="/home/user/leadpilot/.logs/auth.log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date)] Starting auth services..." >> "$LOG"

# Kill only LeadPilot's specific processes (by port, not blanket pkill)
kill $(lsof -ti :8777 2>/dev/null) 2>/dev/null
kill $(lsof -ti :8899 2>/dev/null) 2>/dev/null
# Kill only cloudflared that's proxying LeadPilot's port
ps aux | grep 'cloudflared.*localhost:8777' | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
ps aux | grep 'cloudflared.*localhost:8899' | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 1

# Start auth server
cd /home/user/leadpilot
nohup python3 auth/auth_server.py >> "$LOG" 2>&1 &
echo "[$(date)] auth_server PID: $!" >> "$LOG"
sleep 2

# Start cloudflared tunnel
nohup ~/.local/bin/cloudflared tunnel --url http://localhost:8777 > /tmp/cf_url.txt 2>&1 &
echo "[$(date)] cloudflared PID: $!" >> "$LOG"
sleep 10

# Extract URL with retry (cloudflared may buffer output)
CF_URL=""
for i in 1 2 3; do
    CF_URL=$(grep -o 'https://[a-z0-9.-]*\.trycloudflare\.com' /tmp/cf_url.txt | head -1)
    if [ -n "$CF_URL" ]; then break; fi
    sleep 3
done
if [ -n "$CF_URL" ]; then
    echo "[$(date)] ✅ Tunnel: $CF_URL" >> "$LOG"
    echo "$CF_URL" > /tmp/cf_active_url.txt
else
    echo "[$(date)] ❌ Failed to get tunnel URL" >> "$LOG"
fi

# Verify
if curl -s http://127.0.0.1:8777/health | grep -q '"ok"'; then
    echo "[$(date)] ✅ Auth server healthy" >> "$LOG"
else
    echo "[$(date)] ❌ Auth server not responding" >> "$LOG"
fi
