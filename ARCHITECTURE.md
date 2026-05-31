# 🗺️ 系统架构图 — Smart Tenancy Pro (JB Rental Intel)

> 本文件由 **人类主导**（AI_ARCHITECT_PROTOCOL §2），模块关系变更时同步更新。

---

## 全景数据流

```mermaid
graph TD
    %% ==================== 外部世界 ====================
    subgraph External["🌍 外部系统"]
        FB["📘 FB 群组 ×5"]:::external
        GoogleOAuth["🔑 Google OAuth"]:::external
        WA["💬 WhatsApp"]:::external
        Stripe["💳 Stripe API"]:::external
        User["👤 用户浏览器"]:::external
    end

    %% ==================== 全局上下文 ====================
    subContext["🔄 全局上下文: 定时任务调度 (cron)"]:::context -.->|触发| Stage1
    subContext -.->|触发| Stage2
    subContext -.->|触发| Stage3
    subContext -.->|触发| Stage3B

    %% ==================== 阶段①：数据采集 ====================
    subgraph Stage1["① 数据采集 (Node.js + Puppeteer)"]
        Scraper["fb_scraper.js<br/>浏览器管理 → 5群抓取"]:::module
        RawJSON["fb_posts_raw.json<br/>原始帖文缓存"]:::store
        Scraper -->|写入| RawJSON
    end
    FB -->|HTTP scrape| Scraper

    %% ==================== 阶段②：数据解析 ====================
    subgraph Stage2["② 数据解析 (Python)"]
        Parser["fb_parser.py<br/>字段提取·清洗·分类"]:::module
        CleanJSON["fb_posts_clean.json<br/>清洗后快照"]:::store
    end
    RawJSON --> Parser
    Parser --> CleanJSON

    %% ==================== Google Sheets ====================
    subgraph Sheets["📊 Google Sheets (SA 读写)"]
        SheetPublic["JB Rentals<br/>客户可见 · 房源数据"]:::sheet
        SheetInternal["内部运营<br/>Agent List · 推广记录<br/>授权用户 · 登录会话"]:::sheet
        SheetSub["订阅管理<br/>订阅状态"]:::sheet
    end
    Parser -->|API write| SheetPublic

    %% ==================== 阶段③：推广引擎 ====================
    subgraph Stage3["③ 推广引擎 (Python)"]
        AgentMaint["maintain_agents.py<br/>标准化·去重·更新"]:::module
        Outreach["outreach_engine.py<br/>配额分配·冷却过滤·发送"]:::module
        WADaemon["wa_daemon3.js<br/>Baileys WS :3456"]:::module
    end
    SheetPublic -->|read| AgentMaint
    AgentMaint -->|write| SheetInternal
    SheetInternal -->|read| Outreach
    Outreach -->|wa_sender| WADaemon
    WADaemon -->|WhatsApp msg| WA
    Outreach -->|write 推广记录| SheetInternal

    %% ==================== 阶段④⑤：登录 + 订阅 ====================
    subgraph Stage4["④ 登录认证 (Python + Cloudflare)"]
        HTML["rentals.html<br/>GitHub Pages 托管"]:::frontend
        AuthSrv["auth_server.py<br/>:8777 /preview /google-auth /data"]:::module
        CFTunnel["Cloudflare Tunnel<br/>HTTPS 公网暴露"]:::infra
    end
    User -->|① 打开页面| HTML
    HTML -->|② 无token→GET /preview| CFTunnel
    CFTunnel -->|reverse proxy| AuthSrv
    AuthSrv -->|③ 返回最新8条房源| HTML
    User -->|④ 点击登录→Google OAuth| GoogleOAuth
    GoogleOAuth -->|ID token| HTML
    HTML -->|⑤ POST /google-auth| CFTunnel
    CFTunnel -->|reverse proxy| AuthSrv
    AuthSrv -->|read/write| SheetInternal
    AuthSrv -->|read| SheetSub
    AuthSrv -->|⑥ 返回完整数据| HTML

    subgraph Stage5["⑤ 订阅续费 (Python + SQLite)"]
        SubMgr["sub_mgr/<br/>DB · 逻辑 · 通知"]:::module
        StripeCheck["stripe_checker.py<br/>Stripe 付款验证"]:::module
        SQLite["subscribers.db<br/>订阅者记录"]:::store
    end
    Stripe -->|webhook/check| StripeCheck
    StripeCheck -->|更新状态| SubMgr
    SubMgr --> SQLite
    SubMgr -->|sync| SheetSub
    SubMgr -->|通知到期| WADaemon

    %% ==================== 阶段⑥：主动推送 ====================
    subgraph Stage6["⑥ 订阅推送 (Python)"]
        Notify["notify_subscribers.py<br/>每天3次·早午晚报"]:::module
    end
    SQLite -->|read| Notify
    Notify -->|push| WADaemon
    SheetPublic -->|read统计| Notify

    %% ==================== 日志服务 ====================
    LogSvc["📝 .logs/error.log<br/>统一错误日志"]:::log
    Scraper -.->|异常| LogSvc
    Parser -.->|异常| LogSvc
    Outreach -.->|异常| LogSvc
    AuthSrv -.->|异常| LogSvc
    SubMgr -.->|异常| LogSvc
    WADaemon -.->|异常| LogSvc

    %% ==================== 样式定义 ====================
    classDef module fill:#1e293b,stroke:#6366f1,stroke-width:2px,color:#e2e8f0
    classDef external fill:#0f172a,stroke:#64748b,stroke-width:1px,color:#94a3b8
    classDef store fill:#0f172a,stroke:#f59e0b,stroke-width:1.5px,color:#fbbf24
    classDef sheet fill:#0f172a,stroke:#34d399,stroke-width:1.5px,color:#6ee7b7
    classDef frontend fill:#1e293b,stroke:#22d3ee,stroke-width:2px,color:#67e8f9
    classDef infra fill:#1e293b,stroke:#a855f7,stroke-width:1.5px,color:#c4b5fd
    classDef context fill:#0f172a,stroke:#f87171,stroke-width:2px,color:#fca5a5
    classDef log fill:#0f172a,stroke:#f87171,stroke-width:1px,stroke-dasharray:4 2,color:#fca5a5
```

---

## 模块边界说明

| 层 | 技术栈 | 状态管理 | 典型文件 |
|:---|:-------|:---------|:---------|
| **数据采集** | Node.js 20 + Puppeteer | 文件系统（JSON） | `scraper/fb_scraper.js`, `scraper/lib/` |
| **数据解析** | Python 3.11 + Google API | Google Sheets（SA读写） | `processors/fb_parser.py`, `processors/lib/` |
| **推广引擎** | Python + Baileys WS | 内部运营 Sheet + SQLite | `outreach/outreach_engine.py`, `outreach/lib/` |
| **登录层** | Python http.server + GSI | 内存 session + Sheets | `auth/auth_server.py`, `rentals.html` |
| **订阅管理** | Python + SQLite + Stripe | SQLite + 订阅状态 Sheet | `sub_mgr/`, `stripe_checker.py` |
| **推送通知** | Python + wa_daemon | SQLite + Sheets | `notify_subscribers.py` |

## 数据流向

```
FB群帖 → 爬虫 → JSON → 解析 → Google Sheets(客户可见)
                                    ↓
                              推广引擎 → WhatsApp → Agent
                                    ↓
                            预览模式(8条) → Google登录 → 全文 → Stripe → 续费
                                    ↓
                              每天3次推送 → 订阅用户
```

## 关键约束

- **调用深度 ≤ 4 层**：任何模块链不超过 4 级嵌套
- **禁止循环依赖**：Parser 不调 Outreach，Auth 不调 Scraper
- **双日志制度**：所有 catch 块输出 `.logs/error.log` + console
- **Sheets 是唯一数据中台**：各模块间不直接读写彼此的本地存储
- **SA 统一认证**：所有 Python 模块共用 `/home/user/.hermes/google_sa_rental.json`
