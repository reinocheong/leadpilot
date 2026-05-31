# LeadPilot — JB 房产数据 SaaS

> 从 FB 抓取房源 + Agent 号码 → 数据全公开（电话遮罩）→ Google 登录解锁电话 → WhatsApp 自动推广 → Stripe 付费续费，全链路自动化。

---

## 🏗️ 架构概览

本项目遵循 [`AI_ARCHITECT_PROTOCOL.md`](AI_ARCHITECT_PROTOCOL.md) 规范，采用高度模块化的架构，单文件行数严格控制在 150 行以内。

```
|/home/user/leadpilot/          ← ★ 项目根目录
│
├── 📄 核心 SSOT 文档
│   ├── USER.md                      ← 用户画像与业务价值
│   ├── ARCHITECTURE.md              ← Mermaid 架构全景图
│   ├── JOURNAL.md                   ← 开发流水账
│   ├── MEMORY.md                    ← 避坑指南与技术决策
│   ├── TODO.md                      ← 颗粒化进度追踪
│   ├── README.md                    ← 本文档
│   └── DEPLOY.md                    ← 部署与 Cron 配置
│
├── 🔧 scraper/                      ← 阶段①：FB 爬虫
│   ├── fb_scraper.js                # 主入口 (逐群保存，每群120s超时)
│   └── lib/
│       ├── browser.js               # 浏览器实例管理
│       ├── fb_phone.js              # 电话提取
│       ├── fb_expand.js             # UI 交互
│       └── fb_extract.js            # 数据抓取 (postLink过滤+7套正则)
│
├── 🔧 processors/                   ← 阶段②：数据解析
│   ├── fb_parser.py                 # 主入口 (流程编排)
│   └── lib/
│       ├── field_extractor.py       # 字段提取核心
│       ├── filters.py               # 垃圾帖过滤
│       ├── text_cleaner.py          # UI 噪音清洗
│       └── sheet_writer.py          # Google Sheets 交互
│
├── 🚀 outreach/                     ← 阶段③：推广引擎
│   ├── outreach_engine.py           # 主入口 (配额分配)
│   └── lib/
│       ├── quota_utils.py           # 动态配额算法
│       ├── sheet_reader.py          # 读源数据
│       └── sheet_writer.py          # 写推广记录
│
├── 💳 sub_mgr/                      ← 阶段④⑤：订阅管理 (包结构)
│   ├── __init__.py                  # CLI 入口
│   ├── db.py                        # SQLite CRUD
│   ├── logic.py                     # 业务流程 (开通/到期/续费)
│   └── google_ops.py                # Drive/Sheets 权限管理
│
├── 🔐 auth/                        ← 阶段④：Google 登录认证
│   ├── auth_server.py              # 8777端口 (preview/google-auth/data)
│   └── lib/sheet_ops.py            # Sheets 读取封装
│
├── 📊 scripts/                      ← 辅助脚本
│   ├── export_rentals_json.py       # 导出房源 JSON (975+条)
│   ├── gen_crawler_page.py          # AI 爬虫友好页面
│   ├── gen_sitemap.py               # SEO sitemap
│   ├── summary_report.py            # 状态汇总
│   └── clean_*.py                   # 数据清洗
│
├── 📱 wa/                           ← WhatsApp 通信栈
│   ├── wa_daemon3.js                # 常驻进程 (v3, QR可视化+指数退避)
│   └── lib/
│       └── message_router.js        # 消息分发路由
│
├── 🌐 index.html                    ← 房源浏览页 (数据优先，电话遮罩)
├── 📄 crawler-listings.html         ← AI 爬虫友好版 (974条预渲染)
├── 📄 sitemap.xml                   ← SEO (977 URLs)
├── 💾 data/rentals.json             ← 房源缓存 (自动更新)
├── 📂 .logs/error.log               ← 错误日志
├── 📂 docs/                         ← 开发文档
│   ├── ARCHITECTURE.md / SHEETS.md / WORKFLOW.md / TODO.md
│   ├── 推广文案.md / 推广计划.md
│   └── architecture.html
├── 💳 stripe_checker.py             ← Stripe 付款检测
├── 📋 notify_subscribers.py         ← 订阅推送
├── 💾 subscribers.db                ← SQLite 订阅数据
├── 📦 package.json                  ← Node 依赖
├── 🔒 .env                          ← Stripe Key
└── 🏠 AI_ARCHITECT_PROTOCOL.md      ← 开发协议
```

## 🎯 核心设计原则

| 原则 | 说明 |
|------|------|
| **数据优先** | 访客打开网站即看到全部房源数据（统计、筛选、卡片），无需登录 |
| **电话遮罩** | 所有电话号码显示为 `+601*******`，CSS 模糊 + 🔒 锁定 |
| **点击解锁** | 用户点击遮罩电话才触发 Google 登录，而非一开始就弹登录页 |
| **预览条引导** | 底部固定条提示「🔒 预览 · X 套房源 · 订阅查看联系方式 →」|
| **登录即用** | Google 一键登录后立即解锁电话，3 天试用自动开通 |

## 🛠️ 快速执行

| 阶段 | 任务 | 执行命令 | 说明 |
|:---:|---|---|---|
| ① | 抓取 | `cd /home/user/leadpilot && timeout 300 node scraper/fb_scraper.js` | 约4分钟，自动逐群保存 |
| ② | 解析 | `cd /home/user/leadpilot && timeout 120 python3 processors/fb_parser.py` | 入 Google Sheets |
| ③ | 推广(干跑) | `cd /home/user/leadpilot && python3 outreach/outreach_engine.py` | 不加--send=预览模式 |
| ③ | 推广(发送) | `cd /home/user/leadpilot && python3 outreach/outreach_engine.py --send --slot 1 --total-slots 5` | 发1人 |
| ④ | 订阅管理 | `cd /home/user/leadpilot && python3 sub_mgr.py list` | 查看订阅者 |
| 🔐 | 登录服务 | `cd /home/user/leadpilot && python3 auth/auth_server.py &` | 8777端口 |
| 📊 | 报告 | `cd /home/user/leadpilot && python3 scripts/summary_report.py` | 状态汇总 |

## 🚨 日志与监控

- **控制台：** 实时打印 `[模块名][阶段] 关键快照`。
- **物理文件：** 核心错误记录在 [`.logs/error.log`](.logs/error.log)。

---
> ⚠️ **开发约束：** 修改任何代码前，请务必阅读 [`AI_ARCHITECT_PROTOCOL.md`](AI_ARCHITECT_PROTOCOL.md) 并参考 SSOT 文档。
