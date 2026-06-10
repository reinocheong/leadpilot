# ARCHITECTURE.md — LeadPilot 全景架构

## 🗺️ 系统拓扑图

```mermaid
graph TD
    %% 外部数据源
    FB[(Facebook Groups)] -- "① 采集" --> ScraperCron[FB CloakBrowser 爬虫 cron]

    %% 第一阶段：采集
    subgraph Stage1 [Phase 1: Scraping]
        ScraperCron -->|提取文本/号码| RawJSON[(fb_posts_raw.json)]
    end

    %% 第二阶段：AI 提取
    subgraph Stage2 [Phase 2: AI Extraction]
        RawJSON -- "② AI 提取" --> HermesAI[Hermes AI 逐条提取]
        HermesAI -->|人工对齐确认| Sheets[(Google Sheets: JB Rentals)]
    end

    %% 第三阶段：推广
    subgraph Stage3 [Phase 3: Outreach]
        Sheets -->|读取 Agent| Maintainer[outreach/lib/maintain_agents.py]
        Maintainer --> AgentList[(Agent List)]
        AgentList -- "③ 推广" --> Engine[outreach/outreach_engine.py]
        Engine -->|调用| WADaemon[wa/wa_daemon.js]
        WADaemon -->|发送| WA((WhatsApp))
    end

    %% 第四阶段：数据展示 + 认证
    subgraph Stage4 [Phase 4: Web App & Auth]
        Browser[用户浏览器] -->|访问 index.html| GHPages[GitHub Pages]
        GHPages -->|静态 HTML+JS| Browser
        Browser -->|④a 预览数据（电话遮罩）| PreviewAPI[GET /preview]
        Browser -->|④b 登录解锁电话| AuthAPI[POST /google-auth]
        Browser -->|④c 完整数据（电话可见）| DataAPI[GET /data?token=xxx]
        PreviewAPI -->|读取全部房源| Sheets
        AuthAPI -->|验证 Google Token| AuthServer[auth/auth_server.py]
        AuthServer -->|查/写| SubDB[(授权用户 Sheet)]
        DataAPI -->|验证 Session| AuthServer
        AuthServer -->|读取房源+电话| Sheets
    end

    %% 日志监控
    LogService[.logs/error.log]
    ScraperCron -.-> LogService
    HermesAI -.-> LogService
    Engine -.-> LogService
    AuthServer -.-> LogService

    %% 外部基础设施
    subgraph Infra [Infrastructure]
        Tunnel[Cloudflare Tunnel] -->|公网入口| AuthServer
    end
```

## 🌊 核心数据流

```mermaid
sequenceDiagram
    participant FB as FB 群组
    participant Scraper as 爬虫 (CloakBrowser MCP cron)
    participant AI as Hermes AI 提取
    participant Sheets as Google Sheets
    participant Web as 网页 (index.html)
    participant Auth as 认证服务 (auth_server)
    participant User as 访客/用户

    FB->>Scraper: 滚动抓取帖子文本
    Scraper->>Scraper: 提取电话+链接
    Scraper->>AI: 写入原始 JSON (fb_posts_raw.json)
    AI->>AI: AI 语义理解提取全部字段
    AI->>Sheets: 对齐确认后写入 JB Rentals 表

    Note over Web,Auth: ⭐ 数据优先流程
    User->>Web: 访问 leadpilot.smart-tenancy-pro.org
    Web->>Auth: GET /preview (无需 Token)
    Auth->>Sheets: 读取全部房源
    Sheets-->>Auth: 返回数据（电话明文字段）
    Auth-->>Web: 返回 JSON（电话已遮罩为 +601*******）
    Web->>Web: 渲染全部房源卡片 + 统计 + 筛选器
    Note over Web: 电话显示 🔒 +601******（模糊+点击锁）

    User->>Web: 点击遮罩电话
    Web->>Web: 弹出 Google 登录弹窗
    User->>Auth: Google 登录（POST /google-auth）
    Auth->>Auth: 验证 Google Token，创建 Session
    Auth-->>Web: 返回 Token + 用户信息

    Web->>Auth: GET /data?token=xxx（完整数据）
    Auth->>Sheets: 读取房源（含完整电话）
    Auth-->>Web: 返回数据（电话明文）
    Web->>Web: 刷新页面：电话解锁，可点击拨打
    Web-->>User: 完整功能可用
```

## 🧩 模块依赖与状态边界

- **Global Context (全局状态):** 
    - `Google Sheets`（JB Rentals）: 房源数据的 SSOT。
    - `授权用户 Sheet`: 用户订阅状态。
    - `.env`: 敏感凭据 (Stripe/Google Key)。
    - `AUTH_URL`: `auth.smart-tenancy-pro.org`（CNAME → hermes-webui tunnel，稳定不变）。
- **Local State (局部状态):**
    - `wa_session/`: WhatsApp 认证会话。
    - `fb_posts_raw.json`: 采集阶段的中间缓存（**唯一数据源**）。
    - `sessions`（内存）: auth_server 的登录会话（重启丢失）。

## 🎯 认证与数据访问规则

| 状态 | 可见数据 | 电话 |
|------|---------|------|
| 未登录（预览） | 全部房源 + 统计 + 筛选 | 🚫 遮罩 `+601*******` |
| 已登录 | 全部房源 + 统计 + 筛选 | ✅ 可见，可点击拨打 |

- **登录触发时机**：仅当用户点击遮罩的电话号码时，才弹出 Google 登录
- **不弹登录页**：打开网站直接看到房源数据，没有 login gate
- **预览失败回退**：若 Cloudflare Tunnel 断开导致预览数据获取失败，显示登录页作为兜底

## 🚨 日志与异常边界

- 所有的核心服务 (Auth, Scraper, AI, outreach) 必须捕获异常并写入 `.logs/error.log`。
- 调用深度严禁超过 4 层（例如：Engine -> Sender -> Notify -> Daemon ✅）。
