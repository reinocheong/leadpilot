#!/usr/bin/env bash
# cron_cdp_scraper.sh — CDP FB 爬虫封装脚本
# 通过 cmd.exe 调用 Windows 侧的 CDP 爬虫，结果复制回 WSL
# 需要 Windows Chrome 以 --remote-debugging-port=9222 运行

WIN_SCRIPT="C:\\Users\\User\\Desktop\\fb-cookie-extract\\cdp_scraper.js"
WSL_OUTPUT="/home/user/fb_data/fb_posts_raw.json"
WIN_OUTPUT="C:\\Users\\User\\Desktop\\fb-cookie-extract\\fb_posts_raw.json"

echo "[cron_cdp] 检查 Windows Chrome CDP..."

# 检测 Chrome 是否在线
cmd.exe /c "netstat -ano | findstr 9222" 2>/dev/null | grep LISTENING > /dev/null
if [ $? -ne 0 ]; then
  echo "[cron_cdp] ❌ Chrome CDP 不在线，跳过本次抓取"
  exit 0
fi

echo "[cron_cdp] ✅ Chrome CDP 在线，开始抓取..."

# 运行 Windows 侧 CDP 爬虫
cmd.exe /c "cd /d C:\Users\User\Desktop\fb-cookie-extract && node cdp_scraper.js" 2>&1

# 复制结果回 WSL
if [ -f "$WIN_OUTPUT" ]; then
  cp "$WIN_OUTPUT" "$WSL_OUTPUT"
  POSTS=$(python3 -c "import json; print(len(json.load(open('$WSL_OUTPUT'))))" 2>/dev/null || echo "0")
  echo "[cron_cdp] ✅ 已保存 $POSTS 条到 $WSL_OUTPUT"
else
  echo "[cron_cdp] ⚠️ 未找到输出文件"
fi
