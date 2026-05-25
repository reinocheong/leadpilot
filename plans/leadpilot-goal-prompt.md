# LeadPilot 改名执行 — Goal Prompt

逐层执行以下 6 层改名计划。先读 `/home/user/leadpilot/plans/leadpilot-rename-plan.md` 了解全貌。每完成一层输出 checklist 确认结果，不要跳步。

---

## 第 1 层：GitHub 基础设施

1. 用 `gh repo rename leadpilot` 重命名仓库 `reinocheong/jb-rental-intel` → `reinocheong/leadpilot`
2. 确认 GitHub Pages 重新激活，记下新 URL：`https://reinocheong.github.io/leadpilot/`
3. 在 Cloudflare 配置 301 重定向：`reinocheong.github.io/leadpilot/*` → `reinocheong.github.io/leadpilot/*`
4. 验证：`curl -I https://reinocheong.github.io/leadpilot/rentals.html` 返回 301 且 Location 指向新 URL

**验证：** 旧链接返回 301、新链接 200、Pages 部署成功

---

## 第 2 层：本地文件迁移

1. `mv /home/user/leadpilot /home/user/leadpilot`
2. `cd /home/user/leadpilot && git remote set-url origin git@github.com:reinocheong/leadpilot.git`
3. `git remote -v` 确认 origin 已更新
4. `ls /home/user/leadpilot 2>/dev/null` 确认旧目录不存在

**验证：** 旧路径返回 `No such file`，新路径 `git log -1` 正常

---

## 第 3 层：代码内路径修复（批量替换）

在整个 `/home/user/leadpilot/` 项目内，执行以下全局 grep 并逐个修复：

1. **sys.path.insert(0, "...")** — 全局搜 `jb-rental-intel` 确认所有 Python import 路径已更新
2. **shell 脚本** — 搜 `cd /home/user/leadpilot`，更新为 `/home/user/leadpilot`
3. **.env** — 检查是否有绝对路径引用
4. **rentals.html** — 更新 AUTH_URL 中的 GitHub Pages 路径（`/jb-rental-intel/` → `/leadpilot/`）
5. **outreach 模板 A/B 文案** — 更新推广链接 URL
6. **cron wrapper** — `~/.hermes/scripts/cron_wrappers/` 中所有 `.sh` 文件的 `jb-rental-intel` 路径
7. 所有 cron job 的 workdir 从 `/home/user/leadpilot` → `/home/user/leadpilot`

**验证：** `grep -r 'jb-rental-intel' /home/user/leadpilot/ --include='*.py' --include='*.sh' --include='*.js' --include='*.html' --include='.env'` 返回 0 结果（排除 node_modules 和 wa_session）

---

## 第 4 层：Cron + Crontab 修复

1. `crontab -l` 检查两条 `@reboot` 路径，更新为 `/home/user/leadpilot/`
2. `cronjob action=list` 列出所有 job，对 workdir 含 `/home/user/leadpilot` 的逐个 `cronjob action=update job_id=xxx workdir=/home/user/leadpilot`
3. 对于路径硬编码在 prompt 里的 cron job（如 `run_fb_scraper.sh`），检查 prompt 是否也需要更新

**验证：** 每个 cron job 的 workdir 指向新路径。crontab 中无旧路径残留。

---

## 第 5 层：通知已订阅用户

当前付费用户 0 人，跳过。推广文案中的链接已在第 3 层更新。新推广直接用新链接。

---

## 第 6 层：文档 + 技能 + 记忆扫尾

1. 更新 `/home/user/leadpilot/` 内 7 份 SSOT 文档（README / ARCHITECTURE / DEPLOY / TODO / JOURNAL / MEMORY / USER）中所有 `/home/user/leadpilot` 引用
2. 读 `smart-tenancy-pro` skill 全篇，批量替换 `/home/user/leadpilot` → `/home/user/leadpilot`，项目名 `jb-rental-intel` → `leadpilot`
3. 更新 agent 持久记忆：将目录路径 `jb-rental-intel` → `leadpilot`
4. 更新 wiki 条目（`~/wiki/` 中 JB Rental Intel 相关页面）

**验证：** skill/memory/wiki 中无旧路径引用残留。

---

## 最终验证清单

- [ ] 旧 GitHub 链接返回 301 → 新链接
- [ ] 本地 `/home/user/leadpilot/` 存在，`/home/user/leadpilot` 不存在
- [ ] `git remote -v` 指向 `reinocheong/leadpilot`
- [ ] 代码内无残留 `jb-rental-intel` 路径（grep 确认）
- [ ] 所有 cron job workdir 更新、crontab 更新
- [ ] skill/memory/wiki 已扫尾
- [ ] 爬虫 + auth + wa_daemon 重新启动并健康
