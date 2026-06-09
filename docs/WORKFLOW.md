# WORKFLOW.md — 完整业务自动化工作流

> Smart Tenancy Pro — 从 FB 抓取 → WhatsApp 推广 → 试用 → 付费 → 续费，全链路自动化。  
> 项目根目录：`/home/user/leadpilot/`  
> 最后更新：2026-05-11

---

## 总览：一条完整的赚钱流水线

```
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │                      Smart Tenancy Pro 全自动业务引擎                          │
  │                                                                               │
  │  ┌─────────┐    ┌───────────┐    ┌───────────┐    ┌──────────┐    ┌────────┐ │
  │  │ ① 抓取   │───→│ ② 解析     │───→│ ③ 推广     │───→│ ④ 试用    │───→│ ⑤ 付费  │ │
  │  │ FB群组   │    │ Google    │    │ WhatsApp  │    │ 3天免费   │    │ Stripe │ │
  │  │ 获取号码  │    │ Sheets    │    │ 触达agent │    │ 自动开通   │    │ 自动续  │ │
  │  └─────────┘    └───────────┘    └───────────┘    └──────────┘    └────────┘ │
  │       │              │               │                │               │       │
  │  Agent_Fb_      Agent_Fb_       jb-rental-       jb-rental-     jb-rental-   │
  │  Market_Intel   Market_Intel    intel            intel           intel        │
  └──────────────────────────────────────────────────────────────────────────────┘
```

---

## 统一项目结构

所有代码已合并到 `/home/user/leadpilot/`，不再跨两个目录。

---

## 阶段一：数据采集（抓取 FB 帖子 + 提取号码）

### 脚本

```
leadpilot/scraper/
├── fb_scraper.js        ← 主入口（Node.js + Playwright）
└── lib/
    ├── fb_phone.js      ← 电话号码提取（5组正则 + Unicode归一化）
    ├── fb_expand.js     ← 展开按钮点击（TreeWalker + dispatchEvent 反爬）
    └── fb_extract.js    ← 帖子文本提取
```

### 执行

```bash
cd /home/user/leadpilot/scraper
node fb_scraper.js
```

### 流程

```
启动 Chromium (headless) → 注入 FB Cookies
    │
    ├─ 逐个群组抓取（当前 5 个群组）
    │   ├─ 滚动加载帖子（10轮，无新帖早停）
    │   ├─ 展开前提取（保底数据）
    │   ├─ dispatchEvent 点击所有 "展开" 按钮（两轮）
    │   ├─ 展开后提取（优先数据）
    │   └─ 合并去重
    │
    └─ extractPhone() → 写入 fb_posts_raw.json
```

### 输出

`/home/user/fb_data/fb_posts_raw.json` — 每条帖子含 `group_name`, `agent_name`, `text`, `phone`, `link`, `scraped_at`

---

## 阶段二：数据解析（结构化 → Google Sheets）

### 脚本

```
leadpilot/processors/fb_parser.py   ← 647行，纯规则提取12字段
```

### 执行

```bash
cd /home/user/leadpilot/processors
python3 fb_parser.py
```

### 提取字段

| 列 | 字段 | 说明 |
|:--:|------|------|
| A | Agent Name | 发帖人 |
| B | Property Name | 楼盘名（200+ 已知楼盘 + 5种模式匹配） |
| C | Listing Type | 出租 / 出售 |
| D | Property Type | Studio / 公寓 / 排屋 / 房间 |
| E | Rooms | 几房几厕 |
| F | Furnishing | 全家私 / 半家私 / 无家私 |
| G | Rent (RM) | 租金数字 |
| H | Phone | ★ 推广核心 — agent 电话号码 |
| I | Link | FB 帖子链接 |
| J | Remark | 设施/限制/位置 |
| K | Scraped At | 马来西亚时间 |
| L | Post Text | 清理后原文 |

### 输出

**Google Sheet "JB Rentals"** (`1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM`)

---

## 阶段三：WhatsApp 推广（触达 agent）

### 架构

```
┌─────────────────┐     HTTP POST      ┌──────────────────┐     Baileys      ┌──────────┐
│ outreach_engine  │ ─────────────────→ │  wa_daemon.js    │ ───────────────→ │ WhatsApp │
│ (Python)         │  localhost:3456    │  (Node.js 常驻)   │   WebSocket      │  Cloud   │
└─────────────────┘                    └──────────────────┘                   └──────────┘
        │                                      │
        │ 发消息                               │ 收回复
        ▼                                      ▼
┌─────────────────┐                    ┌──────────────────┐
│  wa_notify.js   │                    │  wa_listener.js  │
│  (CLI 薄封装)    │                    │  (监听回复/注册)  │
└─────────────────┘                    └──────────────────┘
```

### 三层 WhatsApp 栈

| 组件 | 文件 | 职责 |
|------|------|------|
| **Daemon** | `leadpilot/wa_daemon.js` | Baileys 长连接，`localhost:3456`，24/7 在线 |
| **Sender** | `leadpilot/wa_notify.js` | CLI 封装，`node wa_notify.js send <phone> <msg>` |
| **Listener** | `leadpilot/wa_listener.js` | 监听回复 → 检测 agent 回复/注册，更新推广记录 |

### 推广规则（来自 `推广计划.md`）

| 规则 | 值 |
|------|-----|
| 每人每月最多推广 | 1 次（30 天冷却） |
| 每天最多发送 | 5 人（可调） |
| 发送时间 | 每天 10:30 AM |
| 来源 | Google Sheet "JB Rentals" 的 H 列（Phone） |

### 推广引擎（✅ 已完成）

**文件：** `leadpilot/outreach/outreach_engine.py`（142行 + 3 个 lib）

**模块结构：**
```
outreach/
├── outreach_engine.py           ← 主入口，编排完整流程
└── lib/
    ├── wa_sender.py             ← WhatsApp 发送 + A/B/C 3模板
    ├── cooldown_filter.py       ← 30天冷却 + 订阅用户跳过
    └── sheets_tracker.py        ← JB Rentals读取 + 推广记录Sheet自动创建/读写
```

**运行方式：**
```bash
# 干跑验证（不发送，只打印）
python3 outreach/outreach_engine.py

# 正式发送（需要 wa_daemon.js 在运行）
python3 outreach/outreach_engine.py --send

# 自定义发送数量
python3 outreach/outreach_engine.py --send --limit 3
```

**推广记录 Sheet 结构（自动创建）：**
| A: Phone | B: Agent Name | C: Property | D: 模板 | E: 发送时间 | F: 状态 | G: 回复内容 | H: 备注 |
|----------|---------------|-------------|---------|-------------|---------|-------------|---------|

**状态：** 已发送 → 已回复 → 已注册 → 已付费（wa_listener + sub_mgr 自动更新）

| 状态 | 含义 | 触发方式 |
|------|------|----------|
| 已发 | 推广消息已送出 | outreach_engine 自动标记 |
| 已回复 | agent 回了 WhatsApp | wa_listener 检测到回复 → 更新 |
| 已注册 | agent 填了 Google Form | `sub_mgr.py form-process` 检测匹配 → 更新 |
| 已付费 | agent 付了 Stripe | `sub_mgr.py stripe-check` 检测 → 更新 |

---

## 阶段四：试用管理（注册 → 自动开通 → 到期提醒）

### 用户注册路径

```
agent 点击推广链接
    │
    ▼
Google Form 注册页
    ├─ 姓名
    ├─ WhatsApp 号码
    └─ Email 邮箱
    │
    ▼
sub_mgr.py form-process（Cron 定时检查）
    ├─ 读取 Google Form 新回复
    ├─ 去重（.form_processed.json）
    ├─ start_trial(email, name, "standard", phone)
    │   ├─ SQLite 写入 subscribers.db (status="trial", 3天)
    │   ├─ Google Sheet 自动分享（view-only）
    │   └─ WhatsApp 欢迎消息（Baileys）
    └─ sync_subscriber_sheet() → 更新「订阅状态」Sheet
```

### 试用欢迎消息

```
🎉 {name} 你好！

Smart Tenancy Pro 市场雷达 3 天试用已开通！

📊 数据表链接：
https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit

数据每 30 分钟自动更新。
试用期到 {end_date} 截止。

💬 有任何问题直接回复此消息即可

`Ref: trial-{email}`
```

### 到期提醒

```
sub_mgr.py remind（Cron 定时执行）
    ├─ 查询 status='trial' 且 24h 内到期且未提醒过的
    ├─ WhatsApp 发送：
    │   ⏰ {name} 试用快到期了！
    │   Smart Tenancy Pro 市场雷达试用期到 {end_date} 截止。
    │   续费 RM 9.90/月（早鸟价，原价 RM 39.90）：
    │   https://buy.stripe.com/7sY3cu2GOa5u9rp0cI7bW02
    │   付款后自动续期，回复我即可 👌
    └─ 标记 trial_reminded=1
```

### 到期处理

```
sub_mgr.py check（Cron 定时执行）
    ├─ 查询 end_date 已过的 active/trial 用户
    ├─ 状态改为 expired
    ├─ revoke_sheet() → 回收 Google Sheet 访问权限
    └─ WhatsApp 通知：
        👋 {name} 你好，
        Smart Tenancy Pro 市场雷达权限已到期。
        Google Sheet 访问权限已自动回收。
        如需续费，回复此消息即可 🙏
```

---

## 阶段五：付费管理（Stripe 自动续费）

### Stripe 支付流程

```
agent 点击 Stripe 支付链接
    │
    ▼
Stripe Checkout → 付款成功
    │
    ▼
sub_mgr.py stripe-check（Cron 定时执行）
    ├─ 调用 stripe_checker.py
    │   ├─ Stripe API 查询最近 24h 完成的 checkout session
    │   ├─ 去重（processed_payments.txt）
    │   └─ 返回 [{email, name, plan, days}]
    │
    └─ 自动处理：
        ├─ 已有订阅 → renew_subscriber(email, days=30)
        ├─ 新用户 → add_subscriber(email, name, plan)
        │   ├─ SQLite 写入 (status="active")
        │   ├─ Google Sheet 自动分享
        │   └─ WhatsApp 通知（可选）
        └─ 更新 Google Sheet「订阅状态」
```

### Stripe Checkout 链接

```
https://buy.stripe.com/7sY3cu2GOa5u9rp0cI7bW02
```

---

## 全自动 Cron 调度（实际运行中）

| 任务 | 频率 | 执行 | 状态 |
|------|:--:|------|:--:|
| ①+② FB 抓取 + 解析入 Sheets | 每 30 分钟 | `run_fb_scraper.sh` → `fb_scraper.js && fb_parser.py` | ✅ |
| ④ Form 新注册自动开试用 | 每 5 分钟 | `python3 sub_mgr.py form-process` | ✅ |
| ④+⑤ 查付款 + 到期回收 + 试用提醒 | 每 30 分钟 | `python3 sub_mgr.py stripe-check && form-process && check` | ✅ |
| ③ WhatsApp 推广引擎 | 每天 10:30 | `outreach_engine.py` | ❌ 待构建 |
| ④ 试用到期提醒 | 每天 9:00 | `python3 sub_mgr.py remind` | ⚠️ 待配 cron |
| WhatsApp Daemon 常驻 | 24/7 | `node wa_daemon.js` | ⚠️ 待配守护 |

### Cron Job ID 清单

| Job ID | 名称 | 频率 |
|--------|------|:--:|
| `79a141939e36` | FB JB Rental Scraper | */30 |
| `9b344591e084` | Form 自动检查 | */5 |
| `b40c5eb6c39d` | JB Rental Intel 查付款+过期 | */30 |

---

## 数据存储

| 存储 | 位置 | 用途 |
|------|------|------|
| **fb_posts_raw.json** | `/home/user/fb_data/` | 原始 FB 帖子（542条） |
| **JB Rentals Sheet** | Google Sheets `1QgWjlU...` | ★ 结构化房源数据（agent 电话在 H 列） |
| **subscribers.db** | `/home/user/leadpilot/` | SQLite — 订阅者（name/email/phone/plan/status） |
| **推广记录 Sheet** | Google Sheets（待创建） | 推广状态追踪（已发/已回复/已注册/已付费） |
| **订阅状态 Sheet** | Google Sheets `1zLOyuR...` | 订阅状态实时同步 |
| **wa_session/** | `/home/user/leadpilot/wa_session/` | Baileys 认证状态（含 40+ 联系人 @lid 映射） |
| **.form_processed.json** | `/home/user/leadpilot/` | 已处理的 Form 注册邮箱 |
| **processed_payments.txt** | `/home/user/leadpilot/` | 已处理的 Stripe 付款 session ID |

---

## 完整文件清单

```
/home/user/leadpilot/
├── README.md                  ← 技术栈
├── TODO.md                    ← 进度表
├── DEPLOY.md                  ← 部署手册
├── WORKFLOW.md                ← 本文档
├── ARCHITECTURE.md            ← 架构全景
├── AI_ARCHITECT_PROTOCOL.md   ← 开发协议
├── architecture.html          ← 架构可视化
├── 推广计划.md                 ← 推广引擎设计方案
├── 推广文案.md                 ← A/B/C/D 推广文案
├── scraper/                   ← 爬虫（Node.js + Playwright）
│   ├── fb_scraper.js          # 主入口
│   └── lib/
│       ├── fb_phone.js        # 电话提取
│       ├── fb_expand.js       # 展开按钮
│       └── fb_extract.js      # 帖子提取
├── processors/                ← 解析器（Python）
│   ├── fb_parser.py           # ★ 主路径 → Google Sheets
│   ├── process_fb.py          # 备用 → Excel
│   └── process_posts.py       # 旧版（不推荐）
├── scripts/                   ← 辅助
├── sub_mgr.py                 # ★ 订阅管理器（703行，8种命令）
├── stripe_checker.py          # Stripe 付款检测（79行）
├── wa_daemon.js               # WhatsApp Baileys 长连接（167行）
├── wa_notify.js               # WhatsApp CLI 发送（84行）
├── wa_listener.js             # WhatsApp 回复监听
├── outreach/                   ← 推广引擎（✅ 已完成）
│   ├── outreach_engine.py      # ★ 主入口（142行）
│   └── lib/
│       ├── wa_sender.py        # WhatsApp 发送 + 3模板
│       ├── cooldown_filter.py  # 冷却去重
│       └── sheets_tracker.py   # Sheet读写
├── outreach_engine.py         # ✅ 推广引擎（outreach/outreach_engine.py）
├── agent_phones.txt           # 手动整理的 43 个 agent 电话+姓名
├── subscribers.db             # SQLite 订阅数据库
├── .form_processed.json       # 已处理注册去重
├── processed_payments.txt     # 已处理 Stripe 付款去重
├── .env                       # Stripe Secret Key
└── wa_session/                # Baileys 会话状态
```

---

## sub_mgr.py 命令速查

```bash
cd /home/user/leadpilot

# 查所有订阅者
python3 sub_mgr.py list

# 查某人状态
python3 sub_mgr.py status <email>

# 手动开试用
python3 sub_mgr.py trial <email> <name> standard <phone>

# 手动加订阅
python3 sub_mgr.py add <email> <name> standard --phone <phone> --days 30

# 续费
python3 sub_mgr.py renew <email> --days 30

# 检查到期 → 回收
python3 sub_mgr.py check

# 提醒试用将到期
python3 sub_mgr.py remind

# Stripe 付款检测 → 自动续费
python3 sub_mgr.py stripe-check

# Google Form 注册检测 → 自动开试用
python3 sub_mgr.py form-process
```

---

## 待办

| 项目 | 状态 | 优先级 |
|------|:----:|:------:|
| **outreach_engine.py** — 推广引擎 | 📋 待构建 | 🔴 |
| **推广记录 Sheet** — 在 Google Sheets 中创建 | 📋 待创建 | 🔴 |
| Cron 全链路调度配置 | 📋 待配置 | 🔴 |
| wa_listener.js 完善（检测 agent 回复） | 📋 待完善 | 🟡 |
| 各环节日志系统 | 📋 待实现 | 🟡 |
| Cookie 过期告警 | 📋 待实现 | 🟡 |
