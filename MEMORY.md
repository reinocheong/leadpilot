# MEMORY.md — AI 避坑指南与决策记录

## 🛡️ 重大 Bug 死因记录

### 1. 爬虫崩溃与浏览器资源耗尽
- **现象：** `browser has been closed` 或 `page has been closed`。
- **原因：** 每个群组独立启动浏览器导致内存溢出，或 FB 反爬触发重定向到登录页。
- **对策：** 重构为**全局复用一个浏览器实例**，并在 `finally` 块中增加逐层 try/catch，确保单个群组失败不影响后续抓取。

### 2. 推广引擎干跑不发送
- **现象：** Cron 触发了 `outreach_engine.py` 但没有消息送出。
- **原因：** 命令行缺少 `--send` 参数，脚本默认进入 Dry-run 模式。
- **对策：** 在所有 Cron 配置中显式加上 `--send`。

### 3. 数据解析噪音过载
- **现象：** Post Text 列充斥着「火速回复」、「赞评论分享」等冗余信息。
- **原因：** 简单提取 textContent 会带入所有 UI 文本。
- **对策：** 使用 15 条强力正则进行清洗，确保数据纯净。

### 4. Git 提交冲突
- **现象：** `[remote rejected] cannot lock ref`。
- **原因：** 多个 Cron 任务同时尝试 `git push` 修改 `data/rentals.json`。
- **对策：** 统一导出入口，确保同一时间只有一个脚本负责更新并推送数据。

### 5. 登录过渡「跳回登录页」
- **现象：** 用户登录后，骨架屏闪现，然后页面跳回登录页。
- **原因：** 旧流程先 fade 登录页再加载数据。若 `/data` 返回 401，`load()` 直接调用 `showLogin()` 重新显示登录页，用户在骨架屏之后看到登录页闪回。
- **对策：** 新流程 **不提前切画面** —— 登录成功后登录页保留，用跳动圆点动画展示「验证中...」→「加载数据中...」。全部就绪后统一淡出到主界面。加载失败时停动画、显示错误、登录页不动。

### 6. wa_daemon 重连 EADDRINUSE
- **现象：** WA 断线重连时 `startSock()` 再次调用 `http.createServer().listen()`，旧 server 还在监听 → `EADDRINUSE` → 崩溃。
- **原因：** HTTP server 创建在 `startSock()` 函数内部，每次重连都新建。
- **对策：** 2026-05-25 重构：HTTP server 移到模块顶层，只创建一次；`startSock()` 只处理 WhatsApp 连接。

### 7. WA 403 限流 + 指数退避重连
- **现象：** daemon 无限重连（每 5 秒一次）→ WA 服务器返回 `statusCode: 403, location: cln` → 临时封禁连接。
- **原因：** 原始重连逻辑只判断 `!== 401`（登出），不判断 403。5 秒立即重连在被限流时反而加剧封禁。
- **对策：** 2026-05-26 参照另一项目协议重构：
  - **指数退避**：断线后 5min → 10min → 20min → 40min → 60min（上限），通过 `setTimeout` 实现。
  - **403 也停**：`shouldReconnect` 增加 `statusCode !== 403`，403 和 401 都停。
  - **归零**：连接成功（`connection === 'open'`）或生成 QR 码时 `backoffMinutes = 0`。
  - **防多重调度**：设置新定时器前 `clearTimeout(reconnectTimer)`。
  - **不自杀**：原来就没有 `process.exit()`，保持程序挂着等退避。

### 8. 域名 DNS 委托链不兼容 (2026-05-27)
- **现象：** `leadpilot.dpdns.org` (DigitalPlat 免费域名) 在某些 ISP 返回 NXDOMAIN。
- **原因：** DigitalPlat 的 NS (ns1/ns2/ns3.dpdns.org) → Cloudflare NS 的委托链，部分 DNS 解析器（如用户家用路由器 DNS）跟不过去。
- **对策：** 迁移到 Cloudflare 注册的正规域名 `leadpilot.smart-tenancy-pro.org`，A 记录直指 GitHub Pages IP。
- **教训：** 免费域名服务（DigitalPlat）的委托链有兼容性风险，正规域名直接托管在 Cloudflare 更稳定。

### 🔧 诊断教训 (2026-05-27)
- **先检查工具装没装再信结论**：`dig` 未安装时输出空不代表域名不可解析。用 `which dig` 或 Python socket 多路验证。
- **用户说「之前没问题」时不要坚持理论**：先怀疑自己的证据链，重新验证。
- **多路交叉验证 DNS**：系统 DNS + Google DNS API + Cloudflare DNS API，三路一致才算确认。

### 1. 正则 vs LLM 提取
- **决策：** 核心字段（电话、价格、楼盘）优先使用本地正则匹配。
- **理由：** 零成本、零延迟、易于调试。仅在正则无法覆盖的极端复杂场景考虑 LLM。

### 2. 推广配额限制
- **决策：** 每天仅推广 5-10 人，且分 5 个时段。
- **理由：** 马来西亚 WhatsApp 账号成本高，安全第一，牺牲速度换取账号持久度。

### 3. 隧道 URL 自动同步
- **决策：** 通过 `auto_sync_tunnel.sh` 检测 URL 变化并自动 git push 修改 `rentals.html`。
- **理由：** 临时解决方案，避免手动更新 URL。长期应考虑固定二级域名。

## 🤖 AI 行为约束
- **严禁静默重构：** 任何涉及模块拆分或核心逻辑变更的操作，必须先输出 `Proposed Changes`。
- **双日志制度：** 必须同时向 Console 和 `.logs/error.log` 输出结构化日志。
