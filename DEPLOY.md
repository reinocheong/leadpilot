# DEPLOY.md — 部署与环境手册

> 项目：LeadPilot — JB 房产数据 SaaS  
> 根目录：`/home/user/leadpilot/`  
> 最后更新：2026-06-10

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
| 工作目录 | `/home/user/leadpilot/` |

---

## 环境变量

`.env` 文件（根目录，不提交 Git）：

```bash
STRIPE_SECRET_KEY=sk_live_...
```

---

## 数据采集管线

### 1. FB 爬虫（Hermes cron LLM 模式，30分钟自动）

爬虫通过 CloakBrowser MCP 自动抓取 8 个 FB 房产群组。

**Cron Job ID：** `b469bac211e4`
**频率：** 每 30 分钟
**输出：** `/home/user/fb_data/fb_posts_raw.json`
**效果：** 每群 20-30 条，约 150-200 条/轮

### 2. AI 提取（手动执行）

**不再使用 regex 解析器。** 结构化提取由 Hermes AI 语义理解完成。

工作流：
1. 爬虫更新 `fb_posts_raw.json` 后
2. Telegram 通知 Reino
3. Hermes AI（即我）读取原始帖文，逐条理解提取
4. 提取结果展示给 Reino 确认
5. 确认后写入 Google Sheet "JB Rentals"

**质量门禁：未对齐确认，不准写入 Sheet。**

---

## 启动服务

### Auth Server

```bash
cd /home/user/leadpilot
python3 auth/auth_server.py &
```

### WhatsApp Daemon — 指数退避重连

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

```bash
# 查看 Daemon 日志
tail -f .logs/wa_daemon.log

# 重新扫码登录
# 1. 停 daemon 2. 删 wa_session/ 3. 启动 daemon → 扫 QR 码
```

---

## 推广引擎

### A/B 测试

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

## Cron 调度

> 所有 cron 由 Hermes Agent 调度，统一入口 `~/.hermes/cron/jobs.json`。

### 数据采集管线

| Job ID | 模式 | 时间 | 职责 | 状态 |
|--------|------|------|------|:----:|
| `b469bac211e4` | LLM | 每30分 | ①爬虫：8群 → fb_posts_raw.json | 🟢 运行中 |

### 付款与订阅管理

| Job ID | 模式 | 时间 | 职责 |
|--------|------|------|------|
| `b40c5eb6c39d` | no_agent | **每小时** | Stripe 付款检测 + 过期回收 + 用量汇总 |

### 推广引擎

| Job ID | 模式 | 时间 | 职责 | 状态 |
|--------|------|------|------|:----:|
| `266ebb54fc76` | no_agent | 每天 **10:29** | Agent List 去重维护 | 🟢 运行中 |

### 订阅推送

| Job ID | 模式 | 时间 | 职责 |
|--------|------|:----:|------|
| `8027a63fcd89` | no_agent | 每天 **9:00** | 订阅早报（已暂停） |
| `e4b43e14ded2` | no_agent | 每天 **13:00** | 订阅午间推送（已暂停） |
| `d6f04922156f` | no_agent | 每天 **18:00** | 订阅日报推送（已暂停） |

### 已废弃 cron（已删除）

| 原职责 | 删除日期 | 原因 |
|--------|:--------:|------|
| `2093b59a898a` JB Rentals Parser | 2026-06-10 | regex 解析器废弃，改用 AI 提取 |
| `d3a9238b6184` LeadPilot Pipeline | 2026-06-10 | 旧流水线废弃 |
| `025c5513a4ac` 旧版 FB Scraper | 2026-06-10 | 已由 `b469bac211e4` 替代 |
| 导出房源 JSON → git push（每30分） | 2026-05-31 | 已合并到 LLM 爬虫 cron |
| 隧道 URL 自动同步（每5分） | 2026-05-31 | 域名已稳定，不再需要 |

---

## Google Sheets & Forms

### 服务账号认证（永不过期）

| 项目 | 值 |
|------|-----|
| SA Key 文件 | `/home/user/.hermes/google_sa_rental.json` |
| SA 邮箱 | `hermes-agent@gen-lang-client-0782646772.iam.gserviceaccount.com` |
| 权限范围 | Spreadsheets + Drive + Forms |

> ⚠️ 新 Sheet 需要手动共享给 SA 邮箱（编辑者权限）。

### 关键 ID

| 资源 | ID |
|------|-----|
| JB Rentals Sheet（客户可见） | `1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM` |
| 内部运营 Sheet（不共享给客户） | `1gCynpcBHYgoGiRkfVOJOCOjtiOIl0NuGgpyEexAF3W4` |
| Google Form | `1oZTQNl3PF8TOu7RsG2SZeGjx5goT-o2Jy0TL7RlBiIQ` |
| Form Response Sheet | `1zLOyuRbZnycvD0tc4UPLSoR3mfClwkiDOPw3W-v-gXg` |

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

## 故障排查

| 症状 | 可能原因 | 解决 |
|------|----------|------|
| 爬虫 0 条帖子 | FB Cookie 过期 | 提取新 cookie 更新到爬虫 |
| WhatsApp 发不出去 | Daemon 掉线 | 重启 `node wa/wa_daemon3.js` |
| `RefreshError: invalid_scope` | SA Key 没共享给目标 Sheet | 在 Sheet 中共享给 SA 邮箱（编辑者） |
| Stripe 检测不到付款 | Token 过期 | 检查 `.env` 中 `STRIPE_SECRET_KEY` |
| rentals.html 登录报错 | auth_server 挂了 | `curl localhost:8777/health`；重启 `python3 auth/auth_server.py &` |
