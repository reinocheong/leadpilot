# TODO.md — 进度表

## ⏸️ 暂停中（等待 WA 解封）

| 模块 | 任务 | 状态 | 说明 |
|------|------|:----:|------|
| wa_daemon | 403 限流冷却 + 重新扫码 | ⏸️ | WA 返回 403，需等 30min+ 后删 wa_session/ 重新配对 |
| 推广时段①~⑤ | 每天 10:30-14:30 | ⏸️ | 依赖 wa_daemon，已暂停 |
| 订阅午间/日报 | 13:00 / 18:00 | ⏸️ | 依赖 wa_daemon，已暂停 |
| WA 健康检查 | 每小时 10-20 点 | ⏸️ | 依赖 wa_daemon，已暂停 |

## ✅ 已修复

| 模块 | 任务 | 状态 | 日期 |
|------|------|:----:|:----:|
| 域名 | leadpilot.smart-tenancy-pro.org 绑定 + 首页设为房源页 | ✅ | 2026-05-26 |
| wa_daemon | 指数退避重连（5min→60min） | ✅ | 2026-05-26 |
| wa_daemon | 403 停止重连逻辑 | ✅ | 2026-05-26 |
| wa_daemon | EADDRINUSE 修复（server 移出 startSock） | ✅ | 2026-05-25 |
| 改名 | jb-rental-intel → leadpilot | ✅ | 2026-05-25 |
