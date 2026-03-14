# 真实源加固 v1 设计文档

日期：2026-03-11
状态：approved-for-planning

## 1. 背景

当前项目已完成真实外部源接入：
- Eastmoney 和 Sina 的公告/新闻适配器已实现
- 聚合层支持多源合并和 warning 收集
- 手动单股同步链路完整并通过验证

但现有实现还不够健壮：
- 错误消息不够清晰
- 没有重试机制
- Payload 容错性不足
- 只获取第一页数据
- 缺少可观测性

## 2. 本轮目标

本轮定义的加固范围为：**真实源加固 v1（中等加固）**

具体改进：
1. 增强错误消息，包含源名称、stock_code、market、异常类型
2. 添加超时重试机制（单次请求失败时重试 1 次）
3. 提升 Payload 容错性，对可选字段更宽容
4. 支持分页获取（最多前 3 页）
5. 添加 Provider 诊断日志（请求耗时、记录统计）

## 3. 非目标

本轮明确不做：
- 速率限制（当前是手动单股同步，频率低）
- 缓存层（手动触发，不需要缓存）
- Provider 健康检查（暂无定时同步需求）
- 前端 UI 改动
- 批量同步或自动调度

## 4. 技术方案

### 4.1 错误消息增强

**当前实现：**
```python
def _warning_message(source_name: str, exc: Exception) -> str:
    return str(exc) or f"{source_name} failed"
```

**改进方案：**
```python
def _warning_message(
    source_name: str,
    exc: Exception,
    *,
    stock_code: str | None = None,
    market: str | None = None,
) -> str:
    context = f" (stock={market}:{stock_code})" if stock_code and market else ""
    exc_type = type(exc).__name__
    exc_msg = str(exc) or "unknown error"
    return f"{source_name} failed{context}: {exc_type}: {exc_msg}"
```

### 4.2 超时重试

**策略：**
- 单次请求失败时重试 1 次
- 重试间隔：1 秒
- 只重试网络/超时类错误（httpx.TimeoutException, httpx.NetworkError）
- 不重试解析错误（ValueError, KeyError 等）

**实现位置：**
各 source adapter 的 fetch 方法内部，在 HTTP 请求周围包装重试逻辑。

**示例：**
```python
def fetch(self, stock_code: str, market: str, *, since=None):
    for attempt in range(2):  # 最多 2 次尝试
        try:
            response = self._client.get(...)
            response.raise_for_status()
            return self._parse(response, since=since)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == 0:
                time.sleep(1)
                continue
            raise
```

### 4.3 Payload 容错

**当前问题：**
- 可选字段（summary、url）缺失时直接失败
- 必需字段（title、published_at）缺失时错误消息不够清晰

**改进方案：**
- 可选字段缺失时继续处理，记录 warning
- 必需字段缺失时仍然失败，但错误消息包含行号和字段名
- 在 adapter 返回结果时附加 payload 质量 warning

**示例：**
```python
def _parse_rows(rows):
    items = []
    missing_summary_count = 0
    for index, row in enumerate(rows):
        try:
            item = _parse_row(row, index=index)
            if item.summary is None:
                missing_summary_count += 1
            items.append(item)
        except ValueError as exc:
            raise ValueError(f"Row {index}: {exc}")

    warnings = []
    if missing_summary_count > 0:
        warnings.append(f"{missing_summary_count}/{len(rows)} rows missing summary")

    return items, warnings
```

### 4.4 分页支持

**策略：**
- 最多获取前 3 页
- 每页大小：20-50 条（取决于源站 API）
- 合并多页结果后再做 since 过滤和去重
- 如果达到 max_pages 限制，记录 warning

**实现方案：**
各 source adapter 增加可选 `max_pages` 参数（默认 3）。

**示例：**
```python
def fetch(self, stock_code: str, market: str, *, since=None, max_pages=3):
    all_items = []
    warnings = []

    for page in range(1, max_pages + 1):
        response = self._client.get(..., params={"page": page, ...})
        page_items = self._parse(response)

        if not page_items:
            break

        all_items.extend(page_items)

        if page == max_pages and len(page_items) == page_size:
            warnings.append(f"Reached max_pages={max_pages}, more data may exist")

    # 过滤 since
    filtered = [item for item in all_items if since is None or item.published_at >= since]

    return filtered, warnings
```

### 4.5 Provider 诊断日志

**使用 Python logging 模块：**
```python
import logging

logger = logging.getLogger(__name__)

def fetch(self, stock_code: str, market: str, *, since=None):
    start_time = time.time()

    try:
        items, warnings = self._fetch_with_pagination(...)
        elapsed = time.time() - start_time

        logger.info(
            "Provider fetch completed: source=%s stock=%s:%s "
            "elapsed=%.2fs raw_count=%d filtered_count=%d warnings=%d",
            self.__class__.__name__,
            market,
            stock_code,
            elapsed,
            len(all_items),
            len(items),
            len(warnings),
        )

        return items, warnings
    except Exception as exc:
        elapsed = time.time() - start_time
        logger.warning(
            "Provider fetch failed: source=%s stock=%s:%s elapsed=%.2fs error=%s",
            self.__class__.__name__,
            market,
            stock_code,
            elapsed,
            exc,
        )
        raise
```

**日志级别：**
- INFO：正常请求统计
- WARNING：异常情况

**不强制日志配置：**
使用标准 logger，由应用层决定是否配置日志输出。

## 5. 文件变更清单

### 修改文件
- `backend/app/services/providers/eastmoney_announcement.py`
- `backend/app/services/providers/sina_announcement.py`
- `backend/app/services/providers/eastmoney_news.py`
- `backend/app/services/providers/sina_news.py`
- `backend/app/services/providers/aggregate_providers.py`
- `backend/tests/services/test_eastmoney_announcement.py`
- `backend/tests/services/test_sina_announcement.py`
- `backend/tests/services/test_eastmoney_news.py`
- `backend/tests/services/test_sina_news.py`
- `backend/tests/services/test_real_source_aggregate_providers.py`

### 新增文件
无需新增文件，所有改进在现有文件内完成。

## 6. 测试策略

### 6.1 单元测试覆盖

**错误消息增强：**
- 验证 warning 消息包含源名称、stock_code、market、异常类型

**超时重试：**
- 模拟第一次超时、第二次成功的场景
- 模拟两次都超时的场景
- 验证非网络错误不重试

**Payload 容错：**
- 验证可选字段缺失时继续处理
- 验证必需字段缺失时清晰报错
- 验证 payload 质量 warning

**分页支持：**
- 验证多页合并
- 验证达到 max_pages 限制时的 warning
- 验证空页提前终止

**诊断日志：**
- 验证日志调用（使用 unittest.mock 捕获日志）
- 验证日志内容包含关键统计信息

### 6.2 集成测试

- 现有 aggregate provider 测试继续通过
- 现有 sync service 测试继续通过
- 现有 sync API 测试继续通过

## 7. 风险控制

### 7.1 重试可能增加延迟

**风险：** 重试会让单次同步耗时增加（最多增加 1 秒 + 1 次请求时间）

**缓解：** 只重试网络/超时错误，解析错误直接失败。

### 7.2 分页可能获取过多数据

**风险：** 3 页可能有 150+ 条记录，增加内存和处理时间

**缓解：**
- 限制 max_pages=3
- since 过滤在合并后统一做，避免重复处理
- 如果后续发现性能问题，可调整 max_pages 或增加早停逻辑

### 7.3 日志可能泄露敏感信息

**风险：** 日志中包含 stock_code 和 market

**缓解：** 这些是公开信息，不涉及用户隐私或系统密钥。

## 8. 决策摘要

已确认的设计决策：
- 采用中等加固方案（方案 2）
- 错误消息包含源名称、stock_code、market、异常类型
- 超时重试 1 次，间隔 1 秒，只重试网络/超时错误
- Payload 容错：可选字段缺失继续处理，必需字段缺失清晰报错
- 分页支持：最多 3 页，达到限制时记录 warning
- 诊断日志：使用 Python logging，记录请求统计和异常

## 9. 下一步

下一步基于本文档进入 implementation planning：
- 先为错误消息增强、重试、容错、分页、日志拆出可执行任务
- 然后实现各 source adapter 的加固改进
- 最后补充聚焦测试验证
