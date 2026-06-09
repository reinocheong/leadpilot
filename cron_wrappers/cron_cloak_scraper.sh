#!/usr/bin/env bash
# cron_cloak_scraper.sh — CloakBrowser 爬虫封装
# 使用 cloakbrowser npm 包的反检测 stealth，无需 Chrome CDP

cd /home/user/leadpilot || exit 1
OUTPUT="/home/user/leadpilot/.logs/cloak_run.log"
PIDFILE="/tmp/cloak_scraper.pid"

# 防止重叠运行
if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
  echo "[cron_cloak] 上一轮还在跑，跳过"
  exit 0
fi
echo $$ > "$PIDFILE"

echo "[cron_cloak] 开始: $(date)" > "$OUTPUT"

# 5 分钟超时
timeout 360 node scraper/cloak_scraper.mjs >> "$OUTPUT" 2>&1
EXIT=$?

rm -f "$PIDFILE"

if [ $EXIT -eq 0 ]; then
  POSTS=$(python3 -c "import json; print(len(json.load(open('/home/user/fb_data/fb_posts_raw.json'))))" 2>/dev/null || echo "0")
  echo "[cron_cloak] ✅ 完成: $POSTS 条" >> "$OUTPUT"
else
  echo "[cron_cloak] ❌ 失败 (exit=$EXIT)" >> "$OUTPUT"
fi
