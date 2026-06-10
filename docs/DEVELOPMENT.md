# DEVELOPMENT.md — LeadPilot 数据采集开发文档

> 项目：LeadPilot (Smart Tenancy Pro 数据层)
> 最后更新：2026-06-10

---

## 架构变更记录

### ❌ 旧架构（已废弃）

```
CloakBrowser 爬虫 (cron 每30分钟)
        │
        ▼
  fb_posts_raw.json         ← 原始帖文
        │
        ▼
  fb_parser.py (regex)      ← 647 行正则提取
        │
        ▼
  Google Sheet "JB Rentals"  ← 自动写入（无人工校验）
```

**问题：**
- regex 提取质量差 — 楼盘名抓错（`- Sjk` / `40'X80'`）、卖盘误判为出租、售价当租金
- 无人工对齐环节，脏数据直接入 Sheet
- 需要维护 647 行脆弱正则

### ✅ 新架构

```
CloakBrowser 爬虫 (cron 每30分钟)
        │
        ▼
  fb_posts_raw.json         ← 原始帖文（不变）
        │
        ▼
  Hermes AI 提取            ← 我理解帖文语义，逐条提取
        │
        ▼
  对齐确认                  ← 展示给 Reino，确认后才写
        │
        ▼
  Google Sheet "JB Rentals"  ← 高质量数据
```

---

## 工作流详解

### 步骤 1：爬虫 → 原始帖文

- **工具：** CloakBrowser MCP（在 Hermes cron 中运行）
- **Cron Job ID：** `b469bac211e4`（"FB CloakBrowser 爬虫"）
- **频率：** 每 30 分钟
- **输出：** `/home/user/fb_data/fb_posts_raw.json`
- **格式：** `[{text, link, scraped_at}]` — 每条帖文的原始 HTML textContent

### 步骤 2：Hermes AI 提取

由 Hermes Agent（即我）执行，读取 `fb_posts_raw.json`，逐条提取：

| 字段 | 提取方式 | 说明 |
|------|---------|------|
| **Agent Name** | AI 从帖文开头提取 | 发帖人姓名 |
| **Property Name** | AI 理解语义 | 具体楼盘/地点名，不是地区 |
| **Listing Type** | AI 判断 | 出租 / 出售（理解上下文） |
| **Property Type** | AI 识别 | Studio / 公寓 / 排屋 / 半独立 / 房间 等 |
| **Rooms** | AI 提取 | X房Y厕 / X bed Y bath |
| **Furnishing** | AI 判断 | 全家私 / 半家私 / 无家私 |
| **Rent (RM)** | AI 提取 | 仅限出租帖，不含售价/管理费 |
| **Phone** | 爬虫已有，AI 补充 | 帖文中额外号码 |
| **Remark** | AI 总结 | 设施/位置/限制 |
| **Post Text** | 原文 | 清理后的帖文全文 |

**AI 优势：**
- ✅ 售价 vs 租金 — 不会混淆 `RM450,000` 和 `RM800/月`
- ✅ 楼盘名 — 不会把土地尺寸或学校名当楼盘
- ✅ 求租帖 — 一眼识别 `"有没有排屋出租？"` 并跳过
- ✅ 评论帖 — 区分原始帖和评论区回复
- ✅ 卖盘/租盘 — `AVAILABLE FOR SALE` 不会误读为出租

### 步骤 3：对齐确认（质量门）

**铁律：未对齐、未确认，不准写入 Sheet。**

每次提取后，我会向 Reino 汇报：
1. 新帖总数（去重后）
2. 跳过：求租帖 / 卖盘 / 评论帖 / 乱码
3. 高质量可入库数量（有电话+房租+楼盘）
4. 预览 5 条提取结果

Reino 确认 ✅ 后，我才写入 Google Sheet。

### 步骤 4：写入 Sheet

- **Sheet ID：** `1QgWjlUEvFf9auZzptbYI2EEDAeWnKAZcxsXhcCgjJYM`
- **标签页：** `JB Rentals`
- **写入方式：** 覆盖整表（批量写，避免逐条 API 限流）
- **去重：** 按 link / phone / property+rent 三重去重

---

## 文件结构

```
~/fb_data/
  fb_posts_raw.json          ← 爬虫输出（唯一的数据源）

~/leadpilot/
  docs/
    DEVELOPMENT.md            ← 本文档
    WORKFLOW.md               ← 旧工作流文档（已过时，参考 DEVELOPMENT.md）
  data/
    rentals.json              ← Sheet 导出的房源 JSON（只读副本）
```

---

## Cron 任务

| Job ID | 名称 | 频率 | 状态 |
|--------|------|:----:|:----:|
| `b469bac211e4` | FB CloakBrowser 爬虫 | 每 30 分钟 | ✅ 运行中 |
| — | Hermes AI 提取+写 Sheet | 按需，由 Reino 触发 | ⏸ 等待构建 |

> 当前提取+写 Sheet 由我手动执行（Reino 在 Telegram 触发）。
> 未来可考虑 cron 化，但需确保对齐质量门。

---

## 质量门标准

Sheet 内每条数据必须满足以下条件才能保留：

```
必备字段（缺一不可）：
  ☐ Phone（电话）
  ☐ Rent（租金/售价）
  ☐ Property Name（楼盘名）

过滤规则：
  ✗ 求租帖（"找房/寻找/谁有出租"）
  ✗ 非JB地区
  ✗ 卖车/手机等无关帖
  ✗ 评论区回复（无主体帖内容）
  ✗ 乱码（编码错误）
  ✗ 电话为空
```

---

## 清理清单

### 已删除的旧文件

| 文件 | 原因 |
|------|------|
| `~/fb_parser.py` | regex 解析器，不再使用 |
| `~/fb_rental_posts.json` | 旧解析输出，不再使用 |
| `~/fb_batch.mjs` ~ `fb_debug*.mjs` | 调试脚本 |
| `~/fb_merge*.mjs` | 合并脚本（不适用新流程） |
| `~/fb_save.mjs` | 旧保存脚本 |
| `~/fb_list_tools.mjs` | 调试辅助 |
| `~/fb_page_viewer.js` | 旧查看器 |
| `~/fb_data/` 内实验脚本 | 各种试错版本的爬虫/提取脚本 |
| cron `2093b59a898a` | JB Rentals Parser（旧 regex 解析器 cron） |
| cron `d3a9238b6184` | LeadPilot Pipeline（旧流水线 cron） |
| cron `025c5513a4ac` | 旧版 FB Scraper（已由新版替代） |

### 保留的文件

| 文件 | 原因 |
|------|------|
| `~/fb_data/fb_posts_raw.json` | **唯一数据源** — 爬虫输出 |
| cron `b469bac211e4` | 活跃的 CloakBrowser 爬虫 |
| `~/leadpilot/` | 项目根目录，保留架构文档等 |
