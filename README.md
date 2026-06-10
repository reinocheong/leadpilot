# LeadPilot — JB 房产数据 SaaS

> 从 FB 抓取房源 → AI 提取结构化数据 → 人工确认后入 Sheets → 数据全公开（电话遮罩）→ Google 登录解锁电话 → WhatsApp 自动推广 → Stripe 付费续费，全链路自动化。

---

## 🏗️ 架构概览

本项目遵循 [`AI_ARCHITECT_PROTOCOL.md`](AI_ARCHITECT_PROTOCOL.md) 规范，采用高度模块化的架构。

```
/home/user/leadpilot/          ← ★ 项目根目录
│
├── 📄 核心 SSOT 文档
│   ├── USER.md                      ← 用户画像与业务价值
│   ├── ARCHITECTURE.md              ← Mermaid 架构全景图
│   ├── JOURNAL.md                   ← 开发流水账
│   ├── MEMORY.md                    ← 避坑指南与技术决策
│   ├── TODO.md                      ← 颗粒化进度追踪
│   ├── README.md                    ← 本文档
│   └── DEPLOY.md                    ← 部署与环境手册
│
├── 📄 开发文档
│   ├── DEVELOPMENT.md               ← ★ 新工作流（SSOT）
│   ├── WORKFLOW.md                  ← (已过时，参考 DEVELOPMENT.md)
│   └── SHEETS.md                    ← Sheet 清单
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
│   ├── export_rentals_json.py       # 导出房源 JSON
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
├── 📄 crawler-listings.html         ← AI 爬虫友好版
├── 📄 sitemap.xml                   ← SEO
├── 💾 data/rentals.json             ← 房源缓存 (自动更新)
├── 📂 .logs/error.log               ← 错误日志
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
| **AI 提取** | 爬虫只负责抓 raw text，结构化提取由 Hermes AI 语义理解完成 |
| **对齐门禁** | 提取后必须人工确认才写入 Sheet，脏数据不进库 |
| **登录即用** | Google 一键登录后立即解锁电话，3 天试用自动开通 |

## 🛠️ 快速执行

| 阶段 | 任务 | 执行方式 | 说明 |
|:---:|---|---|---|
| ① | 爬虫 | cron `b469bac211e4` 每30分自动跑 | CloakBrowser MCP，8群 |
| ② | AI 提取 | Telegram 通知 Hermes 处理 | 理解语义提取，非 regex |
| ③ | 推广(干跑) | `cd ~/leadpilot && python3 outreach/outreach_engine.py` | 不加--send=预览模式 |
| ③ | 推广(发送) | `cd ~/leadpilot && python3 outreach/outreach_engine.py --send --slot 1 --total-slots 5` | 发1人 |
| ④ | 订阅管理 | `cd ~/leadpilot && python3 sub_mgr.py list` | 查看订阅者 |
| 🔐 | 登录服务 | `cd ~/leadpilot && python3 auth/auth_server.py &` | 8777端口 |
| 📊 | 报告 | `cd ~/leadpilot && python3 scripts/summary_report.py` | 状态汇总 |

## 🚨 日志与监控

- **控制台：** 实时打印 `[模块名][阶段] 关键快照`。
- **物理文件：** 核心错误记录在 [`.logs/error.log`](.logs/error.log)。

---

> ⚠️ **开发约束：** 修改任何代码前，请务必阅读 [`AI_ARCHITECT_PROTOCOL.md`](AI_ARCHITECT_PROTOCOL.md) 并参考 SSOT 文档。
> ⚠️ **数据提取已从 regex 切换为 AI 语义提取** — 不再使用 `fb_parser.py`。
