# SEO 增强方案 — 让 AI 爬虫看到房源数据

## 问题
AI 搜索引擎读首页（SPA）只拿到工具描述 + 收费说明，没有房源数据。
`crawler-listings.html` 有 925 条数据但 AI 爬虫没有充分索引。

## 已做（2026-05-28）

### 1. 首页 index.html 加静态数据样本
位置：`</script>` 后，`<link>` 前，紧接 JSON-LD
内容：6 条真实房源展示 + `RealEstateListing` schema 标记
作用：AI 爬虫不执行 JS 也能读到实际房源数据，不再只看到工具介绍

### 2. crawler-listings.html 加 RealEstateListing 结构化标记
位置：`<head>` 内
内容：JSON-LD 标记 925 条房源为 `RealEstateListing` 数据集
作用：告诉 AI 引擎这是房地产挂牌数据，不是普通页面

## 原理
- AI 搜索引擎（百度AI、元宝、Bing AI 等）读取首页 HTML 时
- 静态 HTML 样本让它们直接提取房源数据
- JSON-LD（realEstateListing）让 AI 引擎理解数据结构
- crawler-listings.html 的 `SameAs` 链接告诉 AI 完整数据集在哪里

## 效果预期
下一次 AI 搜索引擎重新抓取时：
- 搜索「Johor Bahru 租房」「JB rental」等关键词
- AI 应能直接展示房源数据而非工具描述
- 每套房源的价格、楼盘名、类型会被 AI 提取展示
