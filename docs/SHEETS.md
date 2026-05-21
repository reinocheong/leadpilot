# SHEETS.md — Google Sheets 总清单

> 项目：Smart Tenancy Pro  
> 最后更新：2026-05-11

---

## 🔒 内部运营 Sheet（客户不可见）

**ID: `1gCynpcBHYgoGiRkfVOJOCOjtiOIl0NuGgpyEexAF3W4`**

🔗 https://docs.google.com/spreadsheets/d/1gCynpcBHYgoGiRkfVOJOCOjtiOIl0NuGgpyEexAF3W4/edit

| 标签页 | 用途 | 写入者 | 列 |
|------|------|--------|------|
| **Agent List** | 去重后的推广目标清单（每日自动更新） | `maintain_agents.py` | A:Phone · B:Agent · C:FirstSeen · D:LastSeen · E:PostCount · F:Status |
| **推广记录** | 每次 WhatsApp 发送记录（30天冷却依据） | `outreach_engine.py` |

> ③ `maintain_agents.py` 每日从 JB Rentals 提取 → 归一化去重 → 写入 Agent List  
> ④ `outreach_engine.py` 从 Agent List 读 → 过滤冷却 → 发 5 人 → 写推广记录 A:Phone · B:Agent · C:Property · D:模板 · E:发送时间 · F:状态 · G:回复 · H:备注 |

---

## 👥 客户可见 Sheet

**ID: `1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM`**

🔗 https://docs.google.com/spreadsheets/d/1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM/edit

| 标签页 | 用途 | 写入者 |
|------|------|--------|
| **JB Rentals** | FB 爬虫解析后的结构化房源（客户可查看） | `fb_parser.py` |

---

## 📝 Form Response Sheet — 订阅管理

**ID: `1zLOyuRbZnycvD0tc4UPLSoR3mfClwkiDOPw3W-v-gXg`**

| 标签页 | 用途 | 写入者 |
|------|------|--------|
| 第 1 张表单回复 | 试用注册原始响应 | Google Forms |
| 订阅状态 | 订阅状态跟踪（只读，来自 SQLite） | `sub_mgr.py` 同步 ↓ |

> **重要：订阅管理采用方案 B**
> - **SQLite (`subscribers.db`)** 是唯一数据源
> - Sheet「订阅状态」是 **只读副本**，由 `sub_mgr.py` 自动同步
> - 手动修改 Sheet 会被下次同步覆盖
> - `notify_subscribers.py` 每天 9/13/18 读 SQLite 推送 WhatsApp 通知

---

## 📋 Google Form

**ID: `1oZTQNl3PF8TOu7RsG2SZeGjx5goT-o2Jy0TL7RlBiIQ`**

🔗 试用注册表

---

## 🔐 服务账号

| 项目 | 值 |
|------|-----|
| SA 邮箱 | `hermes-agent@gen-lang-client-0782646772.iam.gserviceaccount.com` |
| Key | `/home/user/.hermes/google_sa_rental.json` |
| 已共享 | 全部 ✅ |
