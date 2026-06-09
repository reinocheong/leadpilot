# TODO.md — 进度表

> 项目：LeadPilot（原名 Smart Tenancy Pro / JB Rental Intel）
> 根目录：`/home/user/leadpilot/`
> 最后更新：2026-06-09

---

## 🎯 规范化整改进度

| 阶段 | 描述 | 状态 | 备注 |
|:----|:----|:----:|:----|
| **0** | Git 版本基线 | ✅ | Tag: `pre-refactor-v1` |
| **1** | SSOT 文档补齐 | ✅ | 7 份文档全部到位 |
| **2** | Mermaid 架构图 | ✅ | `ARCHITECTURE.md` |
| **3** | 核心模块化拆分 | [-] | 已拆 `sub_mgr/`，`fb_parser`（1065行）待拆 |
| **4** | 日志系统标准化 | [ ] | 待建 error.log 与统一格式 |
| **5** | 最终审计校验 | [ ] | 待完成 |
| **6** | headless → CloakBrowser MCP | ✅ | fb_scraper.js 退役 → MCP 工具 |

---

## ✅ 近期完成

| 日期 | 事项 |
|:---|:----|
| 2026-05-31 | **爬虫大修** — cookie 过期修复（Win Chrome Control），提取逻辑重构（postLink过滤+7正则），速度优化（4倍），逐群保存，cron切LLM模式 |
| 2026-05-25 | **LeadPilot 改名** — GitHub 仓库/Pages/本地目录/路径/cron/skill/memory/wiki 全部迁移完成 |

---

## 🚀 业务模块进度

| 阶段 | 模块 | 状态 | 关键文件 |
|------|------|:----:|------|
| ① 数据采集 | FB 爬虫 (CloakBrowser MCP) | ✅ | `mcp_cloakbrowser` 工具 |
| ② 数据解析 | 结构化 → Sheets | ✅ | `processors/fb_parser.py` |
| ③ 推广触达 | WhatsApp 推广 | ✅ | `outreach/outreach_engine.py` |
| ④ 试用管理 | 登录/试用/回收 | ✅ | `sub_mgr.py` + `auth/auth_server.py` |
| ⑤ 付费续费 | Stripe 自动续费 | ✅ | `stripe_checker.py` |
| ⑥ 订阅推送 | 每天3次主动推送 | ✅ | `notify_subscribers.py` |

---

## 📝 待办事项清单

### 🔴 高优先级
- [ ] **`fb_parser.py` (1065行) 拆分** — 字段提取、Sheet 写入等模块化
- [ ] **日志系统升级** — 标准化 `.logs/error.log`，审计所有 catch 块

### 🟡 中优先级
- [ ] **`wa_listener.js` 闭环** — agent 回复识别，自动更新推广记录
- [x] **Cookie 过期告警** — 爬虫已切 LLM 模式，自动检测空跑并尝试换 cookie

### 🟢 低优先级
- [ ] **前端代码分离** — `rentals.html` CSS/JS 抽离独立文件
- [ ] **清理冗余脚本** — 审计 `archived/` 和 `scripts/` 中的过期工具
