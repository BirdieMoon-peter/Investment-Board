# Real External Sources Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current empty announcement/news source lists with real Eastmoney and Sina source adapters while preserving the existing manual single-stock sync flow and warning-aware partial-success behavior.

**Architecture:** Keep the existing sync API, aggregate providers, and frontend sync messaging intact. Add focused source adapters plus shared raw types and HTTP helpers, then extend the sync service and dependency wiring to pass stock code and market into the real-source aggregate path without changing the public API shape.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, httpx, BeautifulSoup4, pytest.

---

## File Structure

### Existing files to modify
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/services/providers/announcement_provider.py`
- Modify: `backend/app/services/providers/news_provider.py`
- Modify: `backend/app/services/providers/aggregate_providers.py`
- Modify: `backend/app/services/providers/__init__.py`
- Modify: `backend/app/services/stock_sync.py`
- Modify: `backend/app/api/stocks.py`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`

### New backend files
- Create: `backend/app/services/providers/raw_types.py`
- Create: `backend/app/services/providers/http_client.py`
- Create: `backend/app/services/providers/eastmoney_announcement.py`
- Create: `backend/app/services/providers/sina_announcement.py`
- Create: `backend/app/services/providers/eastmoney_news.py`
- Create: `backend/app/services/providers/sina_news.py`
- Create: `backend/tests/services/test_eastmoney_announcement.py`
- Create: `backend/tests/services/test_sina_announcement.py`
- Create: `backend/tests/services/test_eastmoney_news.py`
- Create: `backend/tests/services/test_sina_news.py`
- Create: `backend/tests/services/test_real_source_aggregate_providers.py`
- Create: `backend/tests/services/test_stock_sync_real_sources.py`

### Responsibility map
- `raw_types.py`: normalized raw provider records before `security_id` is attached.
- `http_client.py`: shared HTTP client factory, headers, timeout, and small response helpers.
- `eastmoney_announcement.py`: Eastmoney announcement fetch + parse + map to `RawAnnouncement`.
- `sina_announcement.py`: Sina announcement fetch + parse + map to `RawAnnouncement`.
- `eastmoney_news.py`: Eastmoney news fetch + parse + map to `RawNewsItem`.
- `sina_news.py`: Sina news fetch + parse + map to `RawNewsItem`.
- `aggregate_providers.py`: call source adapters with `market` and `stock_code`, convert raw records to DB models, deduplicate, collect warnings.
- `stock_sync.py`: pass security metadata through sync path and keep warning semantics.
- `stocks.py`: build real-source providers and pass `security.code`/`security.market` into sync service.

## Chunk 1: Runtime provider foundation

### Task 1: Add runtime parsing dependencies and shared provider primitives

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/services/providers/raw_types.py`
- Create: `backend/app/services/providers/http_client.py`
- Modify: `backend/app/services/providers/announcement_provider.py`
- Modify: `backend/app/services/providers/news_provider.py`
- Modify: `backend/app/services/providers/__init__.py`
- Test: import coverage through later service tests

- [ ] **Step 1: Write the failing import test for shared provider primitives**

```python
from app.services.providers.raw_types import RawAnnouncement, RawNewsItem
from app.services.providers.http_client import build_provider_client
```

- [ ] **Step 2: Run the focused import test to verify it fails**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_real_source_aggregate_providers.py::test_provider_modules_export_real_source_primitives" -q`
Expected: FAIL with import errors because the shared provider files do not exist yet.

- [ ] **Step 3: Promote provider runtime dependencies into the backend package**

```toml
[project]
dependencies = [
  "beautifulsoup4>=4.12,<5.0",
  "fastapi>=0.115,<0.116",
  "httpx>=0.28,<0.29",
  "sqlmodel>=0.0.24,<0.1.0",
  "uvicorn>=0.34,<0.35",
]
```

- [ ] **Step 4: Add normalized raw provider record dataclasses**

```python
@dataclass(frozen=True)
class RawAnnouncement:
    title: str
    published_at: datetime
    source: str
    url: str | None = None
    summary: str | None = None
```

```python
@dataclass(frozen=True)
class RawNewsItem:
    title: str
    published_at: datetime
    source: str
    url: str | None = None
    summary: str | None = None
```

- [ ] **Step 5: Add the shared HTTP client helper and export the new provider primitives**

```python
DEFAULT_PROVIDER_TIMEOUT = 10.0
DEFAULT_PROVIDER_HEADERS = {"User-Agent": "Mozilla/5.0 ..."}

def build_provider_client(*, transport: httpx.BaseTransport | None = None) -> httpx.Client: ...
```

- [ ] **Step 6: Re-run the focused import test**

Run: same pytest command
Expected: PASS

## Chunk 2: Real announcement and news source adapters

### Task 2: Implement Eastmoney and Sina announcement adapters

**Files:**
- Create: `backend/app/services/providers/eastmoney_announcement.py`
- Create: `backend/app/services/providers/sina_announcement.py`
- Create: `backend/tests/services/test_eastmoney_announcement.py`
- Create: `backend/tests/services/test_sina_announcement.py`
- Test: the two new announcement source test files

- [ ] **Step 1: Write the failing Eastmoney announcement adapter tests**

```python
def test_eastmoney_announcement_source_maps_json_rows_to_raw_announcements(): ...
def test_eastmoney_announcement_source_filters_rows_older_than_since(): ...
def test_eastmoney_announcement_source_raises_clear_error_for_bad_payload(): ...
```

- [ ] **Step 2: Write the failing Sina announcement adapter tests**

```python
def test_sina_announcement_source_maps_html_rows_to_raw_announcements(): ...
def test_sina_announcement_source_keeps_absolute_urls(): ...
def test_sina_announcement_source_raises_clear_error_for_missing_markup(): ...
```

- [ ] **Step 3: Run the announcement adapter tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_eastmoney_announcement.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_sina_announcement.py" -q`
Expected: FAIL because the source modules do not exist yet.

- [ ] **Step 4: Implement the Eastmoney announcement adapter with JSON parsing**

```python
class EastmoneyAnnouncementSource:
    def fetch(self, stock_code: str, market: str, *, since: datetime | None = None) -> list[RawAnnouncement]: ...
```

- [ ] **Step 5: Implement the Sina announcement adapter with HTML parsing**

```python
class SinaAnnouncementSource:
    def fetch(self, stock_code: str, market: str, *, since: datetime | None = None) -> list[RawAnnouncement]: ...
```

- [ ] **Step 6: Re-run the announcement adapter tests**

Run: same pytest command
Expected: PASS

### Task 3: Implement Eastmoney and Sina news adapters

**Files:**
- Create: `backend/app/services/providers/eastmoney_news.py`
- Create: `backend/app/services/providers/sina_news.py`
- Create: `backend/tests/services/test_eastmoney_news.py`
- Create: `backend/tests/services/test_sina_news.py`
- Test: the two new news source test files

- [ ] **Step 1: Write the failing Eastmoney news adapter tests**

```python
def test_eastmoney_news_source_maps_json_rows_to_raw_news_items(): ...
def test_eastmoney_news_source_filters_rows_older_than_since(): ...
def test_eastmoney_news_source_raises_clear_error_for_empty_payload(): ...
```

- [ ] **Step 2: Write the failing Sina news adapter tests**

```python
def test_sina_news_source_maps_json_rows_to_raw_news_items(): ...
def test_sina_news_source_normalizes_relative_urls(): ...
def test_sina_news_source_raises_clear_error_for_invalid_rows(): ...
```

- [ ] **Step 3: Run the news adapter tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_eastmoney_news.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_sina_news.py" -q`
Expected: FAIL because the source modules do not exist yet.

- [ ] **Step 4: Implement the Eastmoney news adapter with JSON parsing**

```python
class EastmoneyNewsSource:
    def fetch(self, stock_code: str, market: str, *, since: datetime | None = None) -> list[RawNewsItem]: ...
```

- [ ] **Step 5: Implement the Sina news adapter with JSON parsing**

```python
class SinaNewsSource:
    def fetch(self, stock_code: str, market: str, *, since: datetime | None = None) -> list[RawNewsItem]: ...
```

- [ ] **Step 6: Re-run the news adapter tests**

Run: same pytest command
Expected: PASS

## Chunk 3: Aggregate integration and sync wiring

### Task 4: Pass security metadata through aggregate providers and sync service

**Files:**
- Modify: `backend/app/services/providers/aggregate_providers.py`
- Modify: `backend/app/services/providers/__init__.py`
- Modify: `backend/app/services/stock_sync.py`
- Modify: `backend/app/api/stocks.py`
- Create: `backend/tests/services/test_real_source_aggregate_providers.py`
- Create: `backend/tests/services/test_stock_sync_real_sources.py`
- Modify: `backend/tests/services/test_stock_sync_service.py`
- Modify: `backend/tests/api/test_stock_sync_api.py`
- Test: aggregate + sync service + sync API test files

- [ ] **Step 1: Write the failing aggregate provider integration tests for raw-source conversion**

```python
def test_aggregate_announcement_provider_converts_raw_items_to_models_and_deduplicates(): ...
def test_aggregate_news_provider_collects_source_errors_as_warnings(): ...
def test_provider_modules_export_real_source_primitives(): ...
```

- [ ] **Step 2: Extend the failing stock sync service tests to require stock code and market**

```python
def test_sync_security_passes_security_metadata_to_providers(): ...
def test_sync_security_keeps_warning_aware_partial_success_with_real_aggregate_results(): ...
```

- [ ] **Step 3: Extend the failing sync API test to build real aggregate providers by default**

```python
def test_get_stock_sync_service_builds_real_aggregate_providers(session): ...
```

- [ ] **Step 4: Run the aggregate and sync tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_real_source_aggregate_providers.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_stock_sync_service.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_api.py" -q`
Expected: FAIL because the aggregate providers and sync service still only accept `security_id` and the sync dependency still injects empty source lists.

- [ ] **Step 5: Update aggregate providers to call real source adapters and convert raw records**

```python
class AggregateAnnouncementProvider:
    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        since: datetime | None = None,
    ) -> AnnouncementFetchResult: ...
```

- [ ] **Step 6: Update `StockSyncService.sync_security` to accept security metadata and pass it through**

```python
def sync_security(
    self,
    security_id: int,
    *,
    stock_code: str,
    market: str,
    synced_at: datetime | None = None,
) -> StockSyncResult: ...
```

- [ ] **Step 7: Wire the FastAPI dependency to build real source adapters by default**

```python
def get_aggregate_announcement_provider() -> AggregateAnnouncementProvider:
    return AggregateAnnouncementProvider(
        sources=[
            AnnouncementSourceAdapter("eastmoney", EastmoneyAnnouncementSource()),
            AnnouncementSourceAdapter("sina", SinaAnnouncementSource()),
        ]
    )
```

- [ ] **Step 8: Re-run the aggregate and sync tests**

Run: same pytest command
Expected: PASS

## Chunk 4: Verification and workflow sync

### Task 5: Run real-source verification and update workflow state

**Files:**
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: all real-source backend tests

- [ ] **Step 1: Run the real-source backend verification suite**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_eastmoney_announcement.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_sina_announcement.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_eastmoney_news.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_sina_news.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_real_source_aggregate_providers.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_stock_sync_service.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_api.py" -q`
Expected: PASS

- [ ] **Step 2: Record stable provider decisions if the verification passes**

Add to `memory/decisions.md`:

```md
### Real external sources v1
- Runtime provider fetching uses `httpx` plus `BeautifulSoup` for lightweight parsing.
- Real-source sync passes `market` and `code` through the sync service so source adapters can stay isolated from repository lookups.
```

- [ ] **Step 3: Update progress for the next likely slice**

Set `memory/progress.md` to reflect that real-source adapters are implemented and the next likely slice is either broader provider hardening or a new product module.

## Final Notes
- Keep the sync trigger manual and single-stock only.
- Use mocked HTTP responses in tests; do not hit real external endpoints in automated verification.
- Prefer clear parsing failures and warning messages over silent drops.
- Do not redesign the frontend or public API in this slice.
