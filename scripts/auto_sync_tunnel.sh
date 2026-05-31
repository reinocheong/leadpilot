#!/bin/bash
# auto_sync_tunnel.sh — 静默监听 Cloudflare Tunnel URL 变化，自动更新 rentals.html + push
# 设计：脚本自身产出即消息文本。有变化时输出推送内容，无变化时空输出 → cron 静默。

LOCK_FILE="/tmp/auto_sync_tunnel.lock"
LAST_URL_FILE="/tmp/cf_last_synced_url.txt"
CURRENT_URL_FILE="/tmp/cf_active_url.txt"
RENTALS_HTML="/home/user/leadpilot/index.html"
PROJECT_DIR="/home/user/leadpilot"

exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

# 读当前隧道 URL
if [[ ! -f "$CURRENT_URL_FILE" ]]; then
    exit 0
fi
CURRENT_URL=$(cat "$CURRENT_URL_FILE" | tr -d '\n\r')

# 读上次已同步的 URL
LAST_URL=""
if [[ -f "$LAST_URL_FILE" ]]; then
    LAST_URL=$(cat "$LAST_URL_FILE" | tr -d '\n\r')
fi

# 没变化就静默退出
if [[ "$CURRENT_URL" == "$LAST_URL" ]]; then
    exit 0
fi

# URL 变了 — 更新 index.html（支援有空格和無空格兩種格式）
sed -i "s|const AUTH_URL *= *'https://[^']*';|const AUTH_URL='${CURRENT_URL}';|" "$RENTALS_HTML"

# 验证修改是否生效
if ! grep -qF "$CURRENT_URL" "$RENTALS_HTML"; then
    echo "❌ Tunnel URL 同步失败：sed 替换未命中"
    exit 1
fi

# git commit + push
cd "$PROJECT_DIR"
git add rentals.html
git commit -m "chore: auto-sync tunnel URL → ${CURRENT_URL}" > /dev/null 2>&1
git push > /dev/null 2>&1

if [[ $? -ne 0 ]]; then
    echo "❌ Tunnel URL 已更新但 git push 失败，请手动检查。新URL: ${CURRENT_URL}"
    exit 1
fi

# 记录已同步
echo "$CURRENT_URL" > "$LAST_URL_FILE"

# 静默 — push 成功不输出（空 stdout = cron 不推送）
exit 0
