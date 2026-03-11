# 个股详情闭环 v1 设计文档

日期：2026-03-11
状态：approved-for-planning
来源：`investment_dashboard_plan.md`（产品总方案输入，不替代 workflow source of truth）

说明：本文档是 watchlist MVP 之后的第二阶段跨模块设计产物，用于定义“个股详情闭环 v1”的范围、数据边界与模块推进顺序；实际执行仍以 `docs/02-module-registry.md`、对应模块文档和 `memory/progress.md` 为准。

## 1. 背景

watchlist MVP 已经完成并支持：

- 搜索证券
- 添加 / 删除自选股
- 查看自选股列表
- 本地运行前后端与 seeded SQLite 数据库

下一阶段不再继续扩展列表页，而是围绕“从自选股进入单股详情”构建第二个产品闭环。

## 2. 本轮目标

本轮定义的第二个子项目为：**个股详情闭环 v1**。

首条用户路径为：

1. 用户在自选股列表中看到某只股票
2. 用户点击该股票进入详情页
3. 系统返回该股票的聚合详情数据
4. 用户在详情页查看基础信息、价格上下文与新闻 / 公告
5. 用户可以返回自选股列表继续浏览

本轮要求：

- 入口仅从现有 watchlist 列表进入
- 尽量使用真实数据
- 详情页需包含基础详情、价格上下文、信息聚合区
- 部分数据缺失时，详情页仍应可用
- 详情页应提供清晰的加载、错误、空状态

## 3. 非目标

本轮明确不做以下内容：

- AI 个股分析和推荐结论
- 复杂技术指标体系
- 持仓联动与调仓建议
- 直接按代码打开详情页的独立入口
- grouped watchlists
- 新闻 / 公告的高级分类、摘要生成、情绪分析
- 分钟线、Tick 级实时行情
- 详情页之外的推荐流或复盘系统

## 4. 推荐方案

采用 **“详情页展示优先，按页面最小需求补齐真实数据”** 的推进方式。

### 4.1 方案说明

1. 先定义详情页最小必要的数据结构
2. 补齐数据层中详情页所需的价格上下文与信息聚合实体 / 查询能力
3. 提供聚合型详情 API
4. 最后实现前端详情页与从 watchlist 列表进入的交互

### 4.2 采用该方案的原因

- 与“详情展示优先”的目标一致
- 最大化复用现有 watchlist MVP 架构与代码
- 能把“真实数据”要求收敛到详情页最小必要范围
- 返工最小，交付路径最短

## 5. 模块推进顺序

建议按以下顺序推进：

1. `data-layer`
2. `backend`
3. `frontend`
4. `scripts`（仅当详情真实数据导入或本地 seed 扩展必须引入脚本时补充）

### 5.1 data-layer 职责

- 复用 `securities` 作为主实体入口
- 新增价格上下文实体 / 查询能力
- 新增新闻与公告实体 / 查询能力
- 提供详情聚合所需的数据契约

### 5.2 backend 职责

- 提供单股详情聚合接口
- 统一处理部分数据缺失时的返回策略
- 对不存在证券返回 `404`

### 5.3 frontend 职责

- 在 watchlist 列表中提供进入详情页的交互
- 渲染详情页结构与状态
- 提供返回列表的交互

### 5.4 scripts 职责

- 如有需要，补充详情页真实数据 seed / import / sync 能力
- 如有需要，补充本地 smoke 验证脚本

## 6. 目标架构

第二阶段仍采用单体 Web 应用结构：

```text
Frontend
  watchlist list -> stock detail page
        ↓
Backend API
  GET /api/stocks/{security_id}
        ↓
Data Layer
  securities
  quote_snapshots
  price_bars_daily
  announcements
  news_items
```

### 6.1 架构原则

- 仍然坚持单接口聚合详情页主要数据
- 仅为详情页补齐最小必要数据实体与查询能力
- 新闻 / 公告第一版优先做真实列表数据，不做复杂语义加工
- 价格上下文先支撑详情页趋势展示，不扩展到复杂图表分析系统

## 7. 数据模型设计

### 7.1 复用 `securities`

继续作为详情页主实体入口，保留：

- `id`
- `market`
- `code`
- `name`
- `industry`
- `status`

### 7.2 复用 `quote_snapshots`

继续提供详情页顶部摘要所需的：

- `last_price`
- `change_percent`
- `snapshot_time`

它仍然是“最新快照”来源，而不是价格上下文来源。

### 7.3 新增 `price_bars_daily`

用于提供详情页价格上下文。

建议最小字段：

- `id`
- `security_id`
- `trade_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`
- `created_at`

用途：

- 提供最近一段时间的日线价格上下文
- 支撑详情页趋势展示
- 第一版不引入分钟线

### 7.4 新增 `announcements`

用于详情页公告区。

建议最小字段：

- `id`
- `security_id`
- `title`
- `published_at`
- `source`
- `url`
- `summary`（可为空）
- `announcement_type`（可为空）
- `created_at`

### 7.5 新增 `news_items`

用于详情页新闻区。

建议最小字段：

- `id`
- `security_id`
- `title`
- `published_at`
- `source`
- `url`
- `summary`（可为空）
- `created_at`

## 8. 详情 API 设计

建议新增一个聚合型接口：

## `GET /api/stocks/{security_id}`

### 8.1 返回结构建议

```json
{
  "security": {
    "security_id": 1,
    "market": "SZ",
    "code": "000001",
    "name": "平安银行",
    "industry": "银行",
    "status": "active"
  },
  "latest_quote": {
    "last_price": "10.5000",
    "change_percent": "5.0000",
    "snapshot_time": "2026-03-11T09:30:00"
  },
  "price_context": [
    {
      "trade_date": "2026-03-01",
      "close_price": "10.1000"
    }
  ],
  "announcements": [
    {
      "title": "...",
      "published_at": "...",
      "source": "...",
      "url": "..."
    }
  ],
  "news": [
    {
      "title": "...",
      "published_at": "...",
      "source": "...",
      "url": "..."
    }
  ]
}
```

### 8.2 部分数据缺失策略

接口不应因为单个子区块缺数据而失败。

约定：

- 没有公告 → `announcements: []`
- 没有新闻 → `news: []`
- 没有价格上下文 → `price_context: []`
- 没有最新报价 → `latest_quote: null`

### 8.3 不存在证券

- 返回 `404`

## 9. 前端页面结构

详情页建议分成 4 个区块：

### 9.1 顶部导航区

- 返回自选列表按钮
- 股票名称
- 股票代码
- 行业
- 状态标签（可选）

### 9.2 最新行情摘要区

- 最新价
- 涨跌幅
- 更新时间

### 9.3 价格上下文区

- 最近 N 个价格点
- 前端结构按趋势展示区设计
- 第一版允许用简化可视化，不强求复杂图表能力

### 9.4 信息聚合区

分成：

- 公告区
- 新闻区

每条内容优先展示：

- 标题
- 时间
- 来源
- 链接
- 摘要（若有）

## 10. 前端交互与状态

### 10.1 主路径

1. 用户在 watchlist 列表点击一只股票
2. 进入详情页
3. 页面加载详情数据
4. 用户浏览基础信息、价格上下文、新闻 / 公告
5. 用户返回自选列表

### 10.2 加载状态

- 显示“正在加载个股详情...”

### 10.3 详情不存在 / 404

- 显示“未找到该股票详情”
- 提供返回列表按钮

### 10.4 部分数据缺失

- 没有最新行情 → “暂无最新行情”
- 没有价格上下文 → “暂无价格数据”
- 没有公告 → “暂无公告”
- 没有新闻 → “暂无相关新闻”

### 10.5 请求失败

- 显示“详情加载失败”
- 提供重试按钮
- 提供返回列表按钮

## 11. 测试策略

### 11.1 data-layer

新增测试覆盖：

- `price_bars_daily` 查询顺序与窗口范围
- `announcements` 查询排序
- `news_items` 查询排序
- 空数据返回行为

### 11.2 backend

新增测试覆盖：

- 正常详情返回
- 缺失 `latest_quote`
- 缺失 `price_context`
- 缺失 `announcements`
- 缺失 `news`
- 不存在证券返回 `404`

### 11.3 frontend

新增测试覆盖：

- 从 watchlist 点击进入详情
- 详情加载成功
- 详情加载失败
- 各子区块空状态
- 返回列表按钮
- 局部数据缺失展示

## 12. 风险控制

### 12.1 新闻 / 公告真实接入复杂

第一版优先做：

- 真实列表数据
- 字段简化
- 不做复杂事件分类与摘要生成

### 12.2 价格上下文展示复杂度过高

第一版优先保证：

- 数据正确
- 页面结构正确
- 可视化允许采用最小方案

## 13. 决策摘要

已确认的设计决策：

- 下一阶段为“个股详情闭环 v1”
- 入口仅从 watchlist 列表进入
- 内容包括基础详情、价格上下文、信息聚合区
- 数据策略尽量使用真实数据
- 推进方式选择“详情页展示优先，按页面最小需求补齐真实数据”
- 聚合接口建议为 `GET /api/stocks/{security_id}`
- 部分数据缺失时详情页仍应成功渲染

## 14. 下一步

下一步不直接写代码，而是基于本设计文档进入 implementation planning：

- 先把第二阶段拆成可执行任务
- 明确这一轮先从 `data-layer` 补齐详情所需实体与查询能力开始
- 再继续推进 `backend` 与 `frontend`
