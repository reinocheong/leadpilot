# DEPLOY.md — 部署与环境手册

> 项目：LeadPilot — JB 房产数据 SaaS  
> 根目录：`/home/user/leadpilot/`  
> 最后更新：2026-05-27

---

## 自定义域名

| 项目 | 值 |
|------|-----|
| 域名 | `leadpilot.smart-tenancy-pro.org` |
| 注册商 | Cloudflare Registrar |
| DNS | Cloudflare（NS: indie.ns.cloudflare.com / yadiel.ns.cloudflare.com） |
| 记录 | 4 条 A 记录 → `185.199.108.153` / `109` / `110` / `111`（GitHub Pages，灰色云不代理） |
| GitHub Pages | 自定义域名已验证，CNAME 文件在 repo 根目录 |
| 首页 | `index.html` = rentals.html（房源浏览页） |

Promo 链接格式：`https://leadpilot.smart-tenancy-pro.org/`

---

## 运行环境

| 项目 | 值 |
|------|-----|
| 操作系统 | WSL Ubuntu (Windows Subsystem for Linux) |
| Node.js | v22.22.2 |
| Python | 3.11 (Hermes Agent venv) / 3.12 (系统) |
| Playwright | chromium headless shell 已安装 |
| Baileys | `@whiskeysockets/baileys` 已安装 |
| 工作目录 | `/home/user/leadpilot/` |

---

## 环境变量

`.env` 文件（根目录，不提交 Git）：

```bash
STRIPE_SECRET_KEY=sk_live_...
```

---

## 依赖安装

```bash
cd /home/user/leadpilot

# Node.js 依赖（scraper + WhatsApp）
npm install
# 包含: playwright, @whiskeysockets/baileys

# Playwright 浏览器
npx playwright install chromium

# Python 依赖
pip install google-auth google-api-python-client stripe
```

---

## 启动服务

### Auth Server

```bash
cd /home/user/leadpilot
python3 auth/auth_server.py &
```

### WhatsApp Daemon — 指数退避重连（2026-05-26）

```bash
# 启动（首次会生成 QR 码扫码登录）
node wa/wa_daemon3.js

# 检测 Daemon 健康
curl -s http://localhost:3456/health
# → {"ok":true,"pid":...,"connected":true,"uptime":"..."}
```

**断线时自动指数退避：**
- 5 分钟 → 10 分钟 → 20 分钟 → 40 分钟 → 60 分钟（上限）
- 连接成功后计数器归零
- 登录失效（401）或被限流（403）时停止重连，不无限刷请求
- 不自杀、不重启进程，保持等待

```bash
# 查看 Daemon 日志
tail -f .logs/wa_daemon.log

# 重新扫码登录（如果掉线超过1小时或403）
# 1. 停 daemon
# 2. 删 wa_session/
# 3. 启动 daemon → 扫 QR 码
```

### 2. FB 爬虫（手动运行）

```bash
cd /home/user/leadpilot/scraper
node fb_scraper.js
```

> **2026-05-18 重构：** 改为全局复用 1 个 Chromium 浏览器（而非每个群组启动一个），finally 块逐层 try/catch 防级联崩溃，每群组 60s 超时保护。详见 [README.md#修复记录](README.md)。

### 3. 解析器（手动运行）

```bash
cd /home/user/leadpilot/processors
python3 fb_parser.py
```

## 推广引擎（每天 10:30-14:30 cron 自动跑）

### A/B 测试（2026-05-14 上线）

outreach_engine 奇偶交替发送文案A/B，推广记录 Sheet「模板」列记录。

| 模板 | 定位 | 核心卖点 |
|------|------|----------|
| A | 同行共鸣 | 不用翻群找cobroke，全部agent房源在Sheet里 |
| B | 价值优先 | 搜楼盘名→5秒找到对应agent→WhatsApp谈合作 |

### 手动运行（需 wa_daemon 在线）

```bash
cd /home/user/leadpilot

# 干跑验证（不发送）
python3 outreach/outreach_engine.py

# 正式发送（需 wa_daemon 在线）
python3 outreach/outreach_engine.py --send

# 自定义数量
python3 outreach/outreach_engine.py --send --limit 3
```

---

## 房源浏览页（rentals.html）

### 数据导出脚本

```bash
cd /home/user/leadpilot

# 手动导出（从 JB Rentals Sheet 读数据→JSON，只读不写）
python3 scripts/export_rentals_json.py
# 输出: data/rentals.json (697+条房源)
```

### 自动更新（每30分钟）

Cron 每 30 分钟跑 `scripts/export_rentals_json.py`，仅导出到本地 `data/rentals.json`（不再公开推送）。
数据通过 auth_server 按需提供 — 用户登录后动态获取。

### 登录机制（2026-05-15 新增，2026-05-29 重构为数据优先）

- **预览模式（数据优先）**：未登录用户直接看到全部房源（960+ 条），含统计、筛选、卡片。电话号码显示为 `+601*******`（CSS 模糊 + 🔒 锁定图标）。零登录障碍
- **登录触发**：仅在用户点击遮罩电话或底部预览条「订阅查看联系方式」时，才弹出 Google 登录弹窗
- **登录方式**：Google 一键登录（OAuth），自动创建3天试用
- **后端**：`auth/auth_server.py`（Python HTTP）验证 Google ID token → 查/建内部运营 Sheet「授权用户」tab
- **隧道**：`auth.smart-tenancy-pro.org`（CNAME → hermes-webui tunnel）→ `localhost:8777`，穩定不變
- **Token**：24h 有效，存 localStorage，登录后无需重复输入
- **预览数据源**：auth_server 的 `GET /preview` 端点从 Sheet 实时读取全部房源，对 phone 字段执行遮罩后返回（无需登录）
- **用户管理**：在内部运营 Sheet →「授权用户」tab 加行即可

### 页面特性
- 手机端卡片式布局，纯上下滑动，零横向滚动
- 卡片左侧彩色 accent 条：condo 金色 / landed 绿色 / room 蓝色，一眼区分类型
- 租金琥珀色 pill 标签，今日新房源绿色 NEW 徽章
- 详情彩色 chips（房型紫色、装修绿色），比纯文字更清晰
- 标签换行排列，不横滑
- 关键词搜索（楼盘名/agent/房型/备注）
- agent 行圆形头像 + 号码点击拨打
- 帖子原文展开/收起（超过 80 字折叠）
- 骨架屏加载动画，毛玻璃吸顶 header
- 深色主题，与 architecture.html 风格一致
- 数据驱动：空字段不显示，简洁无冗余

---

## Cron 调度（全链路自动化）

> 所有 cron 由 Hermes Agent 调度，统一入口 `~/.hermes/cron/jobs.json`。
> `no_agent` 模式：纯脚本运行（零 LLM 费用），崩了自动告警。
> 爬虫使用 **CloakBrowser MCP**（反检测 + 持续浏览器服务），LLM 模式每30分钟自动抓取。

### 数据采集管线

| Job ID | 模式 | 时间 | 脚本/命令 | 职责 | 注意 |
|--------|------|------|-----------|------|------|
| `025c5513a4ac` | **LLM** 🧠 | 每30分 | CloakBrowser MCP 抓取 8 群 | ①爬虫+解析+导出一体 | 反检测 + 持久浏览器 |
| `2093b59a898a` | no_agent | 每30分 (:03/:33) | `cron_fb_parser.sh` | ②解析入 Google Sheets | 爬虫的冗余备份 |

### 付款与订阅管理

| Job ID | 模式 | 时间 | 职责 |
|--------|------|------|------|
| `b40c5eb6c39d` | no_agent | **每小时** | Stripe 付款检测 + 过期回收 + 用量汇总 |

### 推广引擎

| Job ID | 模式 | 时间 | 职责 | 状态 |
|--------|------|------|------|:----:|
| `266ebb54fc76` | no_agent | 每天 **10:29** | Agent List 去重维护 | 🟢 运行中 |
| `dcf83dc15887` | no_agent | 每天 **10:30** | 推广时段①（1人） | 🔴 暂停 |
| `f92a5034d8b7` | no_agent | 每天 **11:30** | 推广时段②（1人） | 🔴 暂停 |
| `c69688ec05d2` | no_agent | 每天 **12:30** | 推广时段③（1人） | 🔴 暂停 |
| `83b802670da9` | no_agent | 每天 **13:30** | 推广时段④（1人） | 🔴 暂停 |
| `d144825d5f88` | no_agent | 每天 **14:30** | 推广时段⑤（1人） | 🔴 暂停 |

> 推广暂停原因：WA 账号 463 限制（2026-05-28），冷却中。复查 cron 见下方。

### 订阅推送

| Job ID | 模式 | 时间 | 职责 |
|--------|------|:----:|------|
| `8027a63fcd89` | no_agent | 每天 **9:00** | 订阅早报（主动推送给付费用户） |
| `e4b43e14ded2` | no_agent | 每天 **13:00** | 订阅午间推送 |
| `d6f04922156f` | no_agent | 每天 **18:00** | 订阅日报推送 |

### 监控与报告

| Job ID | 模式 | 时间 | 职责 |
|--------|------|:----:|------|
| `f4db2a8a18e0` | no_agent | **8/12/16/20** 点 | 状态汇总报告 |
| `0726e4d2f86f` | no_agent | 每天 **10-20** 点每小时 | WA daemon 健康检查 |

### 一次性复查

| Job ID | 时间 | 职责 |
|--------|:----:|------|
| `cad5e3e1ccb5` | **2026-06-01 14:00** | WA 463 冷却复查 #2（3天） |
| `c7163ea1eee3` | **2026-06-04 14:00** | WA 463 冷却复查 #3（7天终审） |

### 已废弃 cron（已删除，留档备查）

| 原职责 | 删除日期 | 原因 |
|--------|:--------:|------|
| 导出房源 JSON → git push（每30分） | 2026-05-31 | 已合并到 LLM 爬虫 cron |
| 隧道 URL 自动同步（每5分） | 2026-05-31 | 域名已稳定，不再需要 |

### wrapper 脚本位置

所有 `no_agent` cron 的 wrapper 脚本统一放在：
```
~/.hermes/scripts/cron_wrappers/
```
命名规则：`cron_<功能>.sh`，每个脚本调用对应模块的入口。

---

## Facebook Cookies 管理

### 获取 Cookie

1. Chrome 打开 facebook.com（已登录）
2. F12 → Application → Cookies → facebook.com
3. 复制以下字段：
   - `c_user` — 用户 ID
   - `xs` — 会话 token
   - `fr` — 浏览器指纹
   - `presence` — 在线状态

### 更新 Cookie

编辑 `scraper/fb_scraper.js` 第 21-26 行的 `COOKIES` 数组。

### Cookie 过期症状

- 输出 0 条帖子
- 出现 "browser has been closed"
- 需要重新登录的页面

---

## Google Sheets & Forms

### 服务账号认证（永不过期）

使用 Google Service Account 代替用户 OAuth，无需浏览器授权。

| 项目 | 值 |
|------|-----|
| SA Key 文件 | `/home/user/.hermes/google_sa_rental.json` |
| SA 邮箱 | `hermes-agent@gen-lang-client-0782646772.iam.gserviceaccount.com` |
| 权限范围 | Spreadsheets + Drive + Forms |

> ⚠️ 新 Sheet 需要手动共享给 SA 邮箱（编辑者权限）。SA 自己创建的 Sheet 自动归它所有。

### 关键 ID

| 资源 | ID |
|------|-----|
| JB Rentals Sheet（客户可见） | `1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM` |
| 内部运营 Sheet（不共享给客户） | `1gCynpcBHYgoGiRkfVOJOCOjtiOIl0NuGgpyEexAF3W4` |
| Google Form | `1oZTQNl3PF8TOu7RsG2SZeGjx5goT-o2Jy0TL7RlBiIQ` |
| Form Response Sheet | `1zLOyuRbZnycvD0tc4UPLSoR3mfClwkiDOPw3W-v-gXg` |

### 备份所有 Sheets（操作前必做！）

```bash
GAPI="python3.12 ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py"
BACKUP=~/google_sheets_backup/$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP

$GAPI drive download 1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM --output $BACKUP/JB_Rentals.csv
$GAPI drive download 1zLOyuRbZnycvD0tc4UPLSoR3mfClwkiDOPw3W-v-gXg --output $BACKUP/Form_Responses.csv
```

### 认证检查

```bash
cd /home/user/leadpilot
python3 -c "
from processors.fb_parser import get_sheets_service
svc = get_sheets_service()
r = svc.spreadsheets().get(spreadsheetId='1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM').execute()
print('✅ SA 认证正常:', r.get('properties',{}).get('title','?'))
"
```

---

## sub_mgr.py 常用命令

```bash
cd /home/user/leadpilot

# 查所有订阅者
python3 sub_mgr.py list

# 查某人状态
python3 sub_mgr.py status <email>

# 手动开试用
python3 sub_mgr.py trial <email> <name> standard <phone>

# 手动续费
python3 sub_mgr.py renew <email> --days 30

# 检查到期（回收权限 + WhatsApp 通知）
python3 sub_mgr.py check

# 提醒试用到期
python3 sub_mgr.py remind

# Stripe 付款检测 → 自动续费
python3 sub_mgr.py stripe-check
```

---

## WhatsApp 维护

```bash
# 检查 Daemon 是否在线
curl -s http://localhost:3456/health

# 手动发消息
node wa/wa_notify.js send 60123456789 "测试消息"

# 查看 Daemon 日志
tail -f .logs/wa_daemon.log

# 重新扫码登录（如果掉线）
# 删除 wa_session/ 重新启动 daemon
```

---

## 数据清洗工具

### 电话号格式化

```bash
cd /home/user/leadpilot

# 干跑（预览变更）
python3 scripts/clean_phones.py

# 写入 Sheet
python3 scripts/clean_phones.py --apply
```

一次性清洗（2026-05-14）：471 → +60 国际格式，6 格无效号清空。
Parser 已集成 `normalize_phone()`，新数据自动标准。

### 楼盘名标准化

```bash
cd /home/user/leadpilot

# 干跑
python3 scripts/clean_property_names.py

# 写入 Sheet
python3 scripts/clean_property_names.py --apply
```

一次性清洗（2026-05-14）：391 → 218 独特值，301 行无楼盘名清空。
Parser 已集成 `normalize_property_name()` + `_is_valid_property_name()`，新数据自动标准。

---

## 故障排查

| 症状 | 可能原因 | 解决 |
|------|----------|------|
|| 爬虫 0 条帖子 / 爬虫静默空跑（cron ok 但产出持续 < 3 条） | FB Cookie 过期 | ① 批量关闭所有 Chrome ② Win+R 运行 chrome.exe --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="C:\Users\User\AppData\Local\Google\Chrome\User Data\Default" ③ 在打开的 Chrome 登录 FB ④ WSL 执行 `cmd.exe /c "cd /d C:\Users\User\Desktop\fb-cookie-extract && node get_cookies.js"` ⑤ 将输出的 xs 和 fr 值更新到 scraper/fb_scraper.js 的 COOKIES 数组 |
| `browser has been closed` / `page has been closed` | ① FB Cookie 过期 → 部分群组重定向到登录页 ② 浏览器资源耗尽（多实例同时启动） | ① 更新 Cookie ② 2026-05-18 已重构为单浏览器复用，基本消除 |
| 单个群组超时 | FB 页面加载慢 / DOM 结构变化 / 反爬 | 超时自动跳过不阻塞后续群组，无需手动干预 |
| WhatsApp 发不出去 | Daemon 掉线 | 重启 `node wa/wa_daemon3.js` |
| `RefreshError: invalid_scope` | SA Key 没共享给目标 Sheet | 在 Sheet 中共享给 SA 邮箱（编辑者） |
| Stripe 检测不到付款 | Token 过期 | 检查 `.env` 中 `STRIPE_SECRET_KEY` |
| `googleapiclient` 找不到 | 用错 Python | 使用 Hermes Agent venv 的 `python3` |
| `[remote rejected] cannot lock ref` | 多个 cron 同时 git push 冲突 | 只保留 1 个导出 cron，删掉重复的（2026-05-14 已修复） |
| Post Text 全是 FB 界面噪音 | 旧版 clean_post_text 不够强 | 已重写，新帖自动干净；旧数据跑 `python3 /tmp/clean_batch.py` |
| Agent 名是随机英文（ThrillingGrapefruit） | FB 给匿名用户生成的显示名 | fb_extract.js 自动检测并替换为真实姓名；已有数据跑清理脚本 |
| Rent 列为空但帖文有价格 | ① 价格被清洗函数吃掉 ② MYR 不被识别 | 已修：提取前先读 raw text + 支持 MYR；回填脚本见 /tmp/backfill_v2.py |
| Phone 列格式混乱 | ① 旧数据未清洗 ② 新帖 Parser 未规范化 | ① `python3 scripts/clean_phones.py` ② Parser 已集成（2026-05-14） |
| Sheet 美化后想还原 | 格式太花/不合口味 | `python3 scripts/reset_sheet_format.py` 一键清回裸数据 |
| rentals.html 登录报错 | auth_server 挂了 | 检查 `curl localhost:8777/health`；运行 `python3 auth/auth_server.py &` 重启 |

---

## 辅助脚本速查

| 脚本 | 路径 | 用途 |
|------|------|------|
| Sheet 美化 | `scripts/beautify_sheet.py` | 格式化 Sheet（冻结、斑马纹、条件颜色、列宽） |
| Sheet 还原 | `scripts/reset_sheet_format.py` | 清除所有格式，回到裸数据 |
| 电话号清洗 | `scripts/clean_phones.py` | 一次性清洗 Phone 列 → +60 国际格式 |
| 楼盘名清洗 | `scripts/clean_property_names.py` | 一次性标准化 Property Name + 去垃圾 |
| 租金回填 | `/tmp/backfill_v2.py` | 从 raw JSON 补填空租金（一次性的） |
| Agent 名清理 | `/tmp/clean_agent_only.py` | 清掉FB随机用户名（一次性的） |
| 🔐 Auth 服务 | `python3 auth/auth_server.py &` | 启动 auth_server（后台常驻，无隧道进程） |
| 🔐 手动登录测试 | 打开 `https://leadpilot.smart-tenancy-pro.org/` | 测试用户: test@example.com / test123 |