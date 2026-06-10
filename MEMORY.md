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

### 3. 数据解析噪音过载 (已废弃 — 改用 AI 提取)
- ~~**现象：** Post Text 列充斥着「火速回复」、「赞评论分享」等冗余信息。~~
- ~~**原因：** 简单提取 textContent 会带入所有 UI 文本。~~
- ~~**对策：** 使用 15 条强力正则进行清洗，确保数据纯净。~~
- **现状（2026-06-10）：** 不再需要。爬虫只抓 raw text，AI 语义提取自动忽略 UI 噪音。

### 4. Git 提交冲突
- **现象：** `[remote rejected] cannot lock ref`。
- **原因：** 多个 Cron 任务同时尝试 `git push` 修改 `data/rentals.json`。
- **对策：** 统一导出入口，确保同一时间只有一个脚本负责更新并推送数据。

### 9. headless Playwright / CDP / npm cloakbrowser 退役 → CloakBrowser MCP cron (2026-06-09)
- **问题演变：** headless Playwright 每群~1条 → CDP real Chrome 依赖用户窗口 → cloakbrowser npm 包也是~1条。
- **根因：** FB 对 headless 浏览器的反检测越来越严，只有 CloakBrowser MCP（完整 Playwright MCP + 反检测层）能突破。
- **修复：** 废弃 headless + CDP + cloakbrowser npm 全部方案，改用 **CloakBrowser MCP `browser_run_code_unsafe`**。
- **cron：** Hermes LLM 模式 `b469bac211e4`，每30分。分批抓（每次2群防超时）。
- **效果：** 20-30条/群，**稳定运行无需用户干预**。
- **已删除：** `fb_scraper.js`, `cdp_scraper.js`, `cloak_standalone.mjs`, `cron_cloak_scraper.sh`, `cron_fb_scraper.sh`, `extract_cookies*.js`, `fb_cdp_post.js`, `fb_cdp_win.js`
- **不需要用户保持 Chrome 开着，不需要任何手动操作。**
- **坑：** CloakBrowser 独立脚本（`launch()` + `humanizeBrowser()`）没有 MCP 层的反检测效果，必须用 MCP 工具。
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
| - **教训：** 免费域名服务（DigitalPlat）的委托链有兼容性风险，正规域名直接托管在 Cloudflare 更稳定。

### 10. wa_daemon3.js sock scope 错误 (2026-05-28)
- **现象：** `outreach_engine.py` 发送时每人都报 `❌ sock is not defined`，消息全送不出去。
- **根因：** `wa_daemon3.js` 的 HTTP `/send` 处理器在模块层级检查 `if (!sock)`，但 `sock` 用 `const` 声明在 `startSock()` 函数内（局部变量）→ `ReferenceError`。
- **修复：** 声明模块级 `let sock = null;`，`startSock()` 内改为 `sock = makeWASocket(...)`（去掉 const）。
- **教训：** 跨函数 / HTTP handler 共享的对象必须声明在模块级作用域。daemon 代码中 `sock` 是全局唯一的 WhatsApp 连接，绝不能藏在函数闭包里。

### 9. WA QR 码过期无法扫码 (2026-05-28)
- **现象：** Baileys 生成 QR 码，用户扫了说「二维码已过期」。
- **根因（多因素）：**
  1. **进程提前退出：** gen_qr.js 生成 QR 后 5 秒自动 exit，QR 绑定到已死进程。WhatsApp 服务器拒绝扫码因为连接已终止。
  2. **无即时可视化：** daemon 只输出 QR 文本到 console + /tmp/wa_qr.txt，通过 Telegram 文本传递时超过 20 秒有效窗口。
  3. **端口冲突 EADDRINUSE：** 旧 wa_daemon 占着端口 3456，新 daemon 启动即崩溃，根本没活着等扫码。
  4. **旧 session 残留：** wa_session/ 目录有部分残留数据，Baileys 行为不确定（可能生成无效 QR 或不生成新 QR）。
  5. **auto-clear session：** wa_daemon3.js 每次启动 `rm -rf wa_session/`，清空刚才用户扫码保存的凭据，导致再次启动必须重新扫码。**这是用户重复扫码的根本原因。**
- **对策：**
  - wa_daemon3.js：QR 事件触发时 `spawn('python3') qrcode` 即时生成 /tmp/wa_qr.png
  - HTTP server 在模块顶层（只创建一次），消除重连 EADDRINUSE
  - 启动前 `rm -rf wa_session/` 确保干净状态
  - daemon 保持运行等待扫码（不自主退出）
- **教训：** QR 码配对必须满足三个条件同时成立：① 生成 QR 的进程活着 ② 端口可用 ③ QR 图片及时送达用户。缺任一条件都会让用户看到「过期」。

### 🔧 诊断教训 (2026-05-27/28)
- **先检查工具装没装再信结论**：`dig` 未安装时输出空不代表域名不可解析。用 `which dig` 或 Python socket 多路验证。
- **用户说「之前没问题」时不要坚持理论**：先怀疑自己的证据链，重新验证。
- **多路交叉验证 DNS**：系统 DNS + Google DNS API + Cloudflare DNS API，三路一致才算确认。
- **多因素渐进排查**（2026-05-28 QR 配对教训）：一个问题可能有多个独立根因。不要锁定一个理论就加倍下注。逐一排查：①进程活着吗？②端口可用吗？③依赖/数据干净吗？④输出格式对吗？⑤还有没其他因素？每个都要验，验一个划掉一个，直到找到全部原因。

### 1. ~~正则 vs LLM 提取~~ (2026-06-10 已推翻)
- **旧决策：** 核心字段（电话、价格、楼盘）优先使用本地正则匹配。理由：零成本、零延迟、易于调试。
- **推翻原因：** 正则提取有 4 类无法根治的顽疾 — 楼盘名抓垃圾、卖盘/租盘混淆、售价当租金、英文/中文混合表达漏信息。647 行正则越写越复杂，准确率仍然不达标。
- **新决策：** **全部使用 AI 语义提取**。爬虫只负责抓 raw text，结构化提取由 Hermes AI 理解完成。代价是 token 费和稍慢，但准确率大幅提升。
- **质量门禁：** 提取后必须人工对齐确认才写 Sheet，脏数据不入库。

### 2. 推广配额限制
- **决策：** 每天仅推广 5 人，且分 5 个时段。
- **理由：** 马来西亚 WhatsApp 账号成本高，安全第一，牺牲速度换取账号持久度。

### 3. 隧道 URL 自动同步（已廢除 2026-05-31）
- ~~**决策：** 通过 `auto_sync_tunnel.sh` 检测 URL 变化并自动 git push 修改 `rentals.html`。~~
- ~~**理由：** 临时解决方案，避免手动更新 URL。长期应考虑固定二级域名。~~
- **現狀：** `auth.smart-tenancy-pro.org` CNAME → hermes-webui tunnel，永久穩定，不再需要自動同步

### 11. WA error 463 — 账号级限制 (2026-05-28，已解决)
- **现象：** daemon 连接正常、`/send` 正常，但每条消息报 `error 463: account restricted or missing tctoken for contact`，用户 WhatsApp 看不到消息发出。
- **根因：** 05-26 的 403 封禁后，账号被 WhatsApp 限制「禁止向陌生联系人发起新对话」。重新扫码配对恢复了连接，但没有解除限制。
- **验证线索：** daemon 每次 `sock.sendMessage()` 不抛异常、返回 `{\"ok\":true}`，但 Baileys 异步收到 `error 463`。恢复机制（issuePrivacyTokens）也因账号限制失败。所有发送 `+601****5678` 等测试号均 463，即使同一号码重复发。
- **之前发送成功（05-12~05-19）：** 当时账号未受限，原 wa_daemon.js 正常投递。
- **冷却过程：** 05-28 暂停推广 → 05-29 复查仍 463 → **06-01 复查 463 已消失，恢复正常发送** → 冷却有效，无需换号
- **教训：** WhatsApp 的 403/463 是账号级限制，重新扫码配对只能恢复连接不能恢复发送权限。冷却时间不确定，本次 ~4 天（05-28→06-01）恢复。若 7 天仍 463 才需换号。

## 🤖 AI 行为约束
- **Git push 必須用 Windows Git**：WSL 沒有 GitHub credential helper（`fatal: could not read Username`），必須透過 `/mnt/c/Program\\ Files/Git/bin/git.exe push` 使用 Windows 端儲存的憑證。
- **严禁静默重构：** 任何涉及模块拆分或核心逻辑变更的操作，必须先输出 `Proposed Changes`。
- **双日志制度：** 必须同时向 Console 和 `.logs/error.log` 输出结构化日志。
- **数据优先原则（核心教训 2026-05-29）：** 访客打开网站应直接看到房源数据，不是登录页。登录应发生在「用户需要电话」时才触发。这个项目不是「登录才能看数据」，而是「数据全公开，电话要登录」。SSOT 文档必须明确记录这个设计原则，任何修改都必须从 SSOT 文档开始核验。
- **AI 提取质量门禁（2026-06-10）：** 提取后必须对齐确认才写 Sheet。不自动写 Sheet，不跳过人工确认环节。

### 12. FB cookie 过期 — 静默空跑 (2026-05-31，已修复)
- **现象：** 爬虫 cron `last_status=ok` 但 5 个群全部 0 条，`fb_posts_raw.json` 仅 7KB/8条，备份 212KB/283条，最后更新 12 小时前
- **根因：** FB cookie 中 `xs` 会话 token 过期，Playwright 加载群组被重定向到登录页但不报错
- **诊断：** 手动跑爬虫全部显示「抓取到 0 条」无报错；浏览器打开群组 URL 显示登录页
- **修复：** 用 Windows Chrome Control 提取新 cookie → 更新 `scraper/fb_scraper.js` 中 `xs` 和 `fr` 值
- **自动化：** `C:\\Users\\User\\Desktop\\fb-cookie-extract\\get_cookies.js`（Playwright + CDP 连接真实 Chrome 取 cookie）
- **防护：** 爬虫 cron 切为 LLM 模式，产出 < 3 条自动告警
- **教训：** no_agent 模式无法检测「脚本没崩但产出异常」。静默空跑是最隐蔽的故障。

### 13. Auth Server BrokenPipeError 崩溃 (2026-06-03，已修复)
- **现象：** auth server 每天不定时挂掉，网页显示登录页而非房源数据
- **根因：** Python 内置 `http.server`（`HTTPServer`）的 `BaseHTTPRequestHandler` 在客户端断连时抛 `BrokenPipeError` → 进程死 → tunnel 继续转发返回 502
- **修复：**
  1. 代码：`main()` 函数改为 `while True` + `try/except Exception`，崩了 3s 内自重启
  2. 系统：创建 systemd user service（`leadpilot-auth.service`），`Restart=always` + 开机自启
- **教训：** Python `http.server` 不适合线上使用。`BrokenPipeError` 是常见但隐蔽的崩溃源（进程死但无 traceback 写到日志文件）。生产服务需要（1）代码层自恢复循环（2）系统层守护双重防护。

### 14. Regex → AI 语义提取迁移 (2026-06-10)
- **决策：** 废弃 647 行 regex 解析器 `fb_parser.py`，改为 Hermes AI 逐条理解提取
- **理由：** 正则提取有 4 类无法根治的顽疾：
  1. 楼盘名抓垃圾 — `- Sjk`（学校名）、`40'X80'`（土地尺寸）、地区名当楼盘名
  2. 卖盘误判为出租 — `AVAILABLE FOR SALE` 读成出租，售价 RM1.1mil 当租金 `1100`
  3. 售价当租金 — RM450k、RM1.1m、RM3.5mil 被提取为租金
  4. 英文/混合表达漏信息 — `4 room 2 bath` 漏抓房型
- **优势：** AI 理解语义，能区分售价/租金/管理费、识别正确楼盘名、看懂中英文混合表达
- **代价：** 需要 token 费，不能全自动 cron 跑（需人工对齐确认），但数据质量大幅提升
- **质量门禁：** 提取后展示给 Reino 确认，才写入 Sheet。**严禁自动写 Sheet。**
