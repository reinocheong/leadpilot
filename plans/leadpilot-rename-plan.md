# LeadPilot 改名计划（路线二：彻底换干净）

> 项目根目录 `/home/user/leadpilot/` → 改为 → `/home/user/leadpilot/`  
> GitHub 仓库 `reinocheong/jb-rental-intel` → `reinocheong/leadpilot`  
> GitHub Pages `reinocheong.github.io/leadpilot/` → `reinocheong.github.io/leadpilot/`

---

## 前置：旧链接保护

- 已发给 109 个 agent 的 WhatsApp 链接都指向 `/jb-rental-intel/rentals.html`
- 用 Cloudflare 配 301 重定向：旧 Pages URL → 新 Pages URL
- 旧链接永远不会死，不改名也能继续用

---

## 第 1 层：GitHub 基础设施

1. 重命名仓库 `jb-rental-intel` → `leadpilot`
2. GitHub Pages 重新激活，确认新 URL
3. Cloudflare 配 301：`reinocheong.github.io/leadpilot/*` → `reinocheong.github.io/leadpilot/*`

---

## 第 2 层：本地文件迁移

1. `mv /home/user/leadpilot /home/user/leadpilot`
2. `cd /home/user/leadpilot && git remote set-url origin git@github.com:reinocheong/leadpilot.git`

---

## 第 3 层：代码内路径修复（约 25+ 文件）

批量替换 `/home/user/leadpilot` → `/home/user/leadpilot`：

| 文件类型 | 数量 | 替换内容 |
|---------|:---:|---------|
| `sys.path.insert(0, "...")` | ~12 | 路径 |
| `cd /home/user/leadpilot` | ~10 | shell 脚本路径 |
| `.env` 引用路径 | 1 | 路径 |
| `rentals.html` AUTH_URL | 1 | GitHub Pages 路径 + 产品名 |
| outreach 模板 A/B 文案 | 2 | 推广链接 URL |
| cron wrapper `~/.hermes/scripts/cron_wrappers/` | ~8 | 路径 |

---

## 第 4 层：Cron + Crontab 修复

1. crontab：两条 `@reboot` 路径更新
2. Hermes cron jobs（约 17 个 job）：更新 workdir + 脚本路径

---

## 第 5 层：通知已订阅用户

- 当前付费用户：0 人
- 无需通知，新推广直接用新链接即可

---

## 第 6 层：文档 + 技能 + 记忆扫尾

1. 7 份 SSOT：README / ARCHITECTURE / DEPLOY / TODO / JOURNAL / MEMORY / USER
2. `smart-tenancy-pro` skill（全篇替换 `/home/user/leadpilot`）
3. Agent 持久记忆
4. wiki 条目

---

## 预计风险

| 风险 | 级别 | 应对 |
|:----|:---:|------|
| cron 路径改错导致任务不跑 | 🔴 | 改完逐个跑一次验证 |
| sys.path.insert 改漏 | 🔴 | 全局 grep 确认无遗留 |
| 旧 repo 远程操作错 | 🟡 | 先备份 remote URL |
| 301 配置失败旧链接挂 | 🟡 | 配完先 curl 测试 |
