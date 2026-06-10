# TODO.md — 进度表

> 项目：LeadPilot（原名 Smart Tenancy Pro / JB Rental Intel）
> 根目录：`/home/user/leadpilot/`
> 最后更新：2026-06-10

---

## 🎯 规范化整改进度

| 阶段 | 描述 | 状态 | 备注 |
|:----|:----|:----:|:----|
| **0** | Git 版本基线 | ✅ | Tag: `pre-refactor-v1` |
| **1** | SSOT 文档补齐 | ✅ | 7 份文档全部到位 |
| **2** | Mermaid 架构图 | ✅ | `ARCHITECTURE.md` |
| **3** | ~~核心模块化拆分~~ | 🚫 **已废弃** | `fb_parser.py` 已删除，改用 AI 提取 |
| **4** | 日志系统标准化 | [ ] | 待建 error.log 与统一格式 |
| **5** | 最终审计校验 | [ ] | 待完成 |
| **6** | headless → CloakBrowser MCP | ✅ | fb_scraper.js 退役 → MCP 工具 |

---

## 📝 当前变更（2026-06-10）

### 已完成
- ✅ **提取方式重构**：regex 解析器 `fb_parser.py` 已删除，改为 Hermes AI 语义提取
- ✅ **旧文件清理**：全部废弃脚本（fb_debug*.mjs、fb_batch.mjs、scraper 实验版本等）已删除
- ✅ **旧 cron 清理**：`2093b59a898a` (JB Rentals Parser)、`d3a9238b6184` (LeadPilot Pipeline) 已删除
- ✅ **SSOT 7 文档对齐**：ARCHITECTURE/README/TODO/JOURNAL/MEMORY/DEPLOY/USER 全部更新
- ✅ **DEVELOPMENT.md**：新工作流文档已建立

### 待办
- [ ] **AI 提取首次全量运行**：处理当前 raw JSON 中的新帖，展示效果
- [ ] **Sheet 历史数据清理**：清理旧 regex 留下的脏数据（错楼盘名、售价当租金等）

---

## ✅ 近期完成

| 日期 | 事项 |
|:---|:----|
| 2026-06-10 | **提取方式革命** — 放弃 647 行 regex，改为 Hermes AI 语义理解提取 |
| 2026-05-31 | **爬虫大修** — cookie 过期修复，提取逻辑重构，cron切LLM模式 |
| 2026-05-25 | **LeadPilot 改名** — GitHub/Pages/路径/cron/wiki 全部迁移 |

---

## 🚀 业务模块进度

| 阶段 | 模块 | 状态 | 关键文件 |
|------|------|:----:|------|
| ① 数据采集 | FB 爬虫 (CloakBrowser MCP) | ✅ | `mcp_cloakbrowser` 工具 |
| ② 数据解析 | **AI 语义提取** → Sheets | ✅ (**重构**) | Hermes Agent (我) |
| ③ 推广触达 | WhatsApp 推广 | ✅ | `outreach/outreach_engine.py` |
| ④ 试用管理 | 登录/试用/回收 | ✅ | `sub_mgr.py` + `auth/auth_server.py` |
| ⑤ 付费续费 | Stripe 自动续费 | ✅ | `stripe_checker.py` |
| ⑥ 订阅推送 | 每天3次主动推送 | ✅ | `notify_subscribers.py` |

---

## 📝 待办事项清单

### 🔴 高优先级
- [ ] **AI 提取首次全量运行** — 从 fb_posts_raw.json 提取新帖，对齐后入 Sheet
- [ ] **Sheet 历史数据清洗** — 清理旧 regex 留下的脏数据

### 🟡 中优先级
- [ ] **日志系统升级** — 标准化 `.logs/error.log`，审计所有 catch 块
- [ ] **`wa_listener.js` 闭环** — agent 回复识别，自动更新推广记录

### 🟢 低优先级
- [ ] **前端代码分离** — `rentals.html` CSS/JS 抽离独立文件
