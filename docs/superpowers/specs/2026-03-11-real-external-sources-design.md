# 真实外部源接入 v1 设计文档

日期：2026-03-11
状态：approved-for-planning

## 1. 背景

real-information-provider-v1 已完成聚合框架：
- `AggregateAnnouncementProvider` 和 `AggregateNewsProvider` 就位
- Warning-aware 部分成功链路完整（后端 + 前端）
- 但当前 `sources=[]`，无真实外部源

## 2. 目标

将 source adapter 从空占位实现替换为真实外部数据源适配器：
- 公告：东方财富 + 新浪财经
- 新闻：东方财富 + 新浪财经
- 保持现有聚合框架和同步链路不变

## 3. 非目标

- 不改变 sync API 路径或返回结构
- 不改变前端交互
- 不做自动定时同步
- 不做反爬对抗升级

## 4. 技术方案

### 4.1 依赖变更

- 将 `httpx` 从 `dev` 依赖提升为主依赖（source adapter 运行时需要）
- 新增 `beautifulsoup4` 作为主依赖（HTML 解析）

### 4.2 Provider 协议扩展

当前 provider 协议只接收 `security_id`，但真实源需要 `market` 和 `code` 来构造请求。

解决方案：不修改现有 `AnnouncementProvider` / `NewsProvider` 协议。改为在 aggregate provider 层传入 security 信息：

```python
class AggregateAnnouncementProvider:
    def fetch_for_security(
        self, security_id: int, *, stock_code: str, market: str, since=None
    ) -> AnnouncementFetchResult: ...
```

Source adapter 接口：

```python
class AnnouncementSourceAdapter:
    name: str
    def fetch(self, stock_code: str, market: str, *, since=None) -> list[RawAnnouncement]: ...
```

### 4.3 Source Adapter 实现

#### 4.3.1 公告源

**EastmoneyAnnouncementSource**
- 数据来源：东方财富公告 API
- 技术：httpx GET 请求 → JSON 解析
- 返回字段映射：title, published_at, source, url, summary

**SinaAnnouncementSource**
- 数据来源：新浪财经公告页面
- 技术：httpx GET 请求 → BeautifulSoup HTML 解析
- 返回字段映射：title, published_at, source, url

#### 4.3.2 新闻源

**EastmoneyNewsSource**
- 数据来源：东方财富资讯搜索 API
- 技术：httpx GET 请求 → JSON 解析
- 返回字段映射：title, published_at, source, url, summary

**SinaNewsSource**
- 数据来源：新浪财经新闻 API
- 技术：httpx GET 请求 → JSON 解析
- 返回字段映射：title, published_at, source, url, summary

### 4.4 容错策略

- 每个 source adapter 的 HTTP 请求超时：10 秒
- User-Agent 设置为标准浏览器 UA
- 单源异常被 aggregate provider 捕获为 warning
- 解析失败返回空列表 + warning

### 4.5 中间数据结构

```python
@dataclass
class RawAnnouncement:
    title: str
    published_at: datetime
    source: str
    url: str | None = None
    summary: str | None = None

@dataclass
class RawNewsItem:
    title: str
    published_at: datetime
    source: str
    url: str | None = None
    summary: str | None = None
```

Aggregate provider 负责将 `RawAnnouncement` / `RawNewsItem` 转换为 `Announcement` / `NewsItem` 模型（填入 security_id）。

### 4.6 同步链路变更

`stocks.py` 的 `sync_stock` 端点：
1. 已有 security 对象（用于 404 检查）
2. 传 `security.code` 和 `security.market` 给 sync service
3. Sync service 传给 aggregate provider

## 5. 文件变更清单

### 修改文件
- `backend/pyproject.toml` - 依赖变更
- `backend/app/services/providers/aggregate_providers.py` - 接收 stock_code/market
- `backend/app/services/providers/announcement_provider.py` - 重构为 source adapter 接口
- `backend/app/services/providers/news_provider.py` - 重构为 source adapter 接口
- `backend/app/services/providers/__init__.py` - 导出新模块
- `backend/app/services/stock_sync.py` - 传递 stock_code/market
- `backend/app/api/stocks.py` - 传递 security 信息给 sync service，注入真实源

### 新增文件
- `backend/app/services/providers/raw_types.py` - RawAnnouncement/RawNewsItem
- `backend/app/services/providers/eastmoney_announcement.py`
- `backend/app/services/providers/sina_announcement.py`
- `backend/app/services/providers/eastmoney_news.py`
- `backend/app/services/providers/sina_news.py`
- `backend/app/services/providers/http_client.py` - 共享 HTTP 客户端配置
- `backend/tests/services/test_eastmoney_announcement.py`
- `backend/tests/services/test_sina_announcement.py`
- `backend/tests/services/test_eastmoney_news.py`
- `backend/tests/services/test_sina_news.py`
- `backend/tests/services/test_real_aggregate_providers.py`

## 6. 测试策略

- 所有 source adapter 测试使用 mock HTTP 响应（不做真实网络请求）
- 每个 adapter 测试覆盖：成功解析、超时处理、解析失败处理
- 集成测试验证 aggregate provider 注入真实源后的合并行为
- 现有 sync service 和 API 测试保持通过

## 7. 决策摘要

- 使用 httpx + BeautifulSoup 技术栈
- 公告源：东方财富 API + 新浪财经页面
- 新闻源：东方财富搜索 API + 新浪财经 API
- 中间数据结构隔离外部源差异
- 不修改原有 provider 协议，在 aggregate 层扩展参数
