# 真实信息源聚合 v1 设计文档

日期：2026-03-11
状态：approved-for-planning
来源：`investment_dashboard_plan.md`（产品总方案输入，不替代 workflow source of truth）

说明：本文档是 stock detail v1 与 information-sync v1 之后的下一阶段跨模块设计产物，用于定义“真实信息源聚合 v1”的范围、Provider 架构、同步结果策略与模块推进顺序；实际执行仍以 `docs/02-module-registry.md`、对应模块文档和 `memory/progress.md` 为准。

## 1. 背景

当前项目已经完成：

- watchlist MVP
- stock detail v1
- local runnable integration
- information-sync v1（手动单股同步）

目前同步链路已经具备完整形态：

- 前端详情页可手动触发同步
- 后端有 `POST /api/stocks/{security_id}/sync`
- 数据层支持公告 / 新闻增量写入

但当前 provider 仍是 stub provider，尚未接入真实外部源。

## 2. 本轮目标

本轮定义的下一阶段子项目为：**真实信息源聚合 v1**。

首条用户路径为：

1. 用户在 stock detail 页点击“同步最新信息”
2. 后端调用多个公告 / 新闻真实来源 provider
3. Provider 聚合层合并结果并做最小去重
4. 数据写入本地数据库
5. 详情页刷新并展示真实同步后的公告 / 新闻

本轮要求：

- 公告和新闻都接入真实源
- 每类信息优先接入多个来源并合并
- 以抓取成功率优先
- 保持 `POST /api/stocks/{security_id}/sync` 接口路径不变
- 读详情接口与同步接口继续保持分离

## 3. 非目标

本轮明确不做以下内容：

- 批量同步整个 watchlist
- 自动定时同步 / 调度器
- 复杂来源优先级打分系统
- NLP 摘要、情绪分析、事件分类
- 高级文本相似度去重
- 前端大改版
- 详情页之外的推荐、持仓、AI 结论

## 4. 推荐方案

采用 **“Provider 聚合层先行，多来源合并与最小去重优先”** 的推进方式。

### 4.1 方案说明

1. 为公告与新闻分别定义多个 source adapter
2. 为每类信息定义一个 aggregate provider
3. aggregate provider 负责调用多个来源、合并结果、规则去重、输出 warning
4. 现有 sync service 继续负责写库与返回同步摘要

### 4.2 采用该方案的原因

- 最符合“抓取成功率优先”目标
- 不改变当前同步 API 和详情页交互
- 让外部源差异被隔离在 provider 层
- 后续新增 / 替换来源的成本最低

## 5. 模块推进顺序

建议按以下顺序推进：

1. `backend`
2. `data-layer`（随 backend 同步推进，但重点不再是新增实体，而是 upsert / provider 对接）
3. `frontend`
4. `scripts`（仅在 provider 验证或 demo 数据扩展需要脚本时介入）

### 5.1 backend 职责

- 新增 source adapter
- 新增 aggregate provider
- 让 sync service 切换到真实 provider
- 增强同步返回结构中的 warning / synced_at 等字段

### 5.2 data-layer 职责

- 复用现有 `announcements` 与 `news_items`
- 完善最小去重 / upsert 支持
- 支持多来源结果的增量写入

### 5.3 frontend 职责

- 继续复用现有同步按钮
- 轻量显示同步 warning / 部分成功信息
- 不重做详情页结构

### 5.4 scripts 职责

- 如需要，补 provider 调试或本地联调脚本
- 如需要，扩展 demo 数据 seed

## 6. Provider 架构设计

### 6.1 三层结构

#### Source Adapter
每个真实来源一个 adapter，例如：

- `AnnouncementSourceA`
- `AnnouncementSourceB`
- `NewsSourceA`
- `NewsSourceB`

每个 adapter 只负责：

- 请求来源
- 解析来源数据
- 转成统一中间结构

#### Aggregate Provider
为每类信息定义：

- `AggregatedAnnouncementProvider`
- `AggregatedNewsProvider`

职责：

- 调多个 adapter
- 收集结果
- 合并排序
- 做最小去重
- 输出标准化记录与 warning

#### Sync Service
`StockSyncService` 继续只负责：

- 调 provider
- 拿标准化记录
- 调 repository upsert
- 返回同步摘要

## 7. 标准化记录结构

### 7.1 公告标准化结构

至少包含：

- `title`
- `published_at`
- `source`
- `url`
- `summary`
- `announcement_type`（可空）

### 7.2 新闻标准化结构

至少包含：

- `title`
- `published_at`
- `source`
- `url`
- `summary`

## 8. 去重策略

### 8.1 公告去重

优先按以下组合判断重复：

- `title`
- `published_at`
- `url`

若 URL 缺失，则退化为：

- `title`
- `published_at`

### 8.2 新闻去重

优先按以下组合判断重复：

- `title`
- `published_at`
- `source`

必要时退化为：

- `title`
- `published_at`

### 8.3 为什么不做复杂相似度去重

本轮目标是多源拉通与成功率优先，复杂相似度去重会增加：

- 实现复杂度
- 测试复杂度
- 错杀风险

因此第一版坚持规则型最小去重。

## 9. 同步接口返回结构

接口路径保持不变：

## `POST /api/stocks/{security_id}/sync`

返回结构建议增强为：

```json
{
  "security_id": 1,
  "synced": true,
  "announcements_upserted": 4,
  "news_items_upserted": 7,
  "warnings": [
    "announcement source B failed",
    "news source A timeout"
  ],
  "synced_at": "2026-03-11T14:00:00"
}
```

### 9.1 部分成功策略

- 单个 source 失败，不应导致整个 provider 失败
- 至少一个 source 成功时，provider 仍可返回结果
- 只有该类全部 source 都失败时，才视为该类同步失败

### 9.2 不存在 security

- 返回 `404`

## 10. 前端交互策略

前端继续复用现有 stock detail 页同步按钮。

新增 / 强化的行为：

- 同步成功时显示数量摘要与 warning 信息
- 同步失败时显示错误信息
- 同步成功后继续刷新详情页

前端不需要在这一轮重做结构。

## 11. 分阶段实施顺序

### 第 1 步：先搭聚合框架

- provider 接口
- aggregate provider
- warning 返回结构
- 部分成功 / 全失败测试

### 第 2 步：先接公告多源

- `AnnouncementSourceA`
- `AnnouncementSourceB`
- `AggregatedAnnouncementProvider`

### 第 3 步：再接新闻多源

- `NewsSourceA`
- `NewsSourceB`
- `AggregatedNewsProvider`

### 第 4 步：sync service 切换到真实 provider

- 保持上层 API 不变
- 保持前端调用不变

## 12. 测试策略

### 12.1 backend

新增测试覆盖：

- 多来源 provider 合并
- 单个 source 失败时仍可部分成功
- 全部 source 失败时的失败路径
- 规则型最小去重
- sync API warning / synced_at 返回

### 12.2 frontend

新增测试覆盖：

- 同步结果中 warning 的展示
- 部分成功提示
- 同步后详情继续刷新

## 13. 风险控制

### 13.1 多来源字段质量不一致

通过标准化中间结构隔离来源差异。

### 13.2 某个来源经常失败

第一版允许 warning 存在，不强求所有来源同时成功。

### 13.3 去重误差

第一版采用规则型最小去重，先以“避免大量明显重复”为目标，不追求语义级精确去重。

## 14. 决策摘要

已确认的设计决策：

- 下一阶段为“真实信息源聚合 v1”
- 公告与新闻都接真实源
- 每类优先接多个来源并合并
- 抓取成功率优先
- 继续保留 `POST /api/stocks/{security_id}/sync`
- 继续保持详情读取与同步写入分离
- 采用 provider 聚合层架构与规则型最小去重

## 15. 下一步

下一步不直接写代码，而是基于本文档进入 implementation planning：

- 先为 provider / aggregate provider / warning 返回结构拆出可执行任务
- 然后实现公告与新闻真实源接入
- 最后补前端同步结果提示增强
