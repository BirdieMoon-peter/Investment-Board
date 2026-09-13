# Real Source Hardening v1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden existing real external source adapters with better error messages, retry logic, payload tolerance, pagination support, and diagnostic logging.

**Architecture:** Enhance the four existing source adapters (Eastmoney/Sina for announcements/news) in place without changing their public interfaces. Add retry logic, pagination, and logging within each adapter. Update aggregate provider warning messages to include context. Keep all changes backward compatible.

**Tech Stack:** Python 3.12, httpx, pytest, Python logging module.

---

## File Structure

### Existing files to modify
- Modify: `backend/app/services/providers/eastmoney_announcement.py`
- Modify: `backend/app/services/providers/sina_announcement.py`
- Modify: `backend/app/services/providers/eastmoney_news.py`
- Modify: `backend/app/services/providers/sina_news.py`
- Modify: `backend/app/services/providers/aggregate_providers.py`
- Modify: `backend/tests/services/test_eastmoney_announcement.py`
- Modify: `backend/tests/services/test_sina_announcement.py`
- Modify: `backend/tests/services/test_eastmoney_news.py`
- Modify: `backend/tests/services/test_sina_news.py`
- Modify: `backend/tests/services/test_real_source_aggregate_providers.py`

### No new files needed
All improvements are in-place enhancements to existing adapters.

## Chunk 1: Error message enhancement and aggregate provider context

### Task 1: Enhance aggregate provider warning messages with context

**Files:**
- Modify: `backend/app/services/providers/aggregate_providers.py`
- Modify: `backend/tests/services/test_real_source_aggregate_providers.py`
- Test: `backend/tests/services/test_real_source_aggregate_providers.py`

- [ ] **Step 1: Write failing test for enhanced warning messages**

```python
def test_aggregate_announcement_provider_includes_context_in_warnings():
    security_id = 7
    stock_code = "600519"
    market = "sh"

    class FailingSource:
        def fetch(self, stock_code: str, market: str, *, since=None):
            raise ValueError("upstream unavailable")

    provider = AggregateAnnouncementProvider(
        raw_sources=[RawAnnouncementSourceAdapter("test-source", FailingSource())]
    )

    result = provider.fetch_for_security(
        security_id, stock_code=stock_code, market=market
    )

    assert len(result.warnings) == 1
    assert "test-source" in result.warnings[0]
    assert "sh:600519" in result.warnings[0]
    assert "ValueError" in result.warnings[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/services/test_real_source_aggregate_providers.py::test_aggregate_announcement_provider_includes_context_in_warnings" -v`
Expected: FAIL because current warning message doesn't include stock_code/market context

- [ ] **Step 3: Update _warning_message helper to include context**

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

- [ ] **Step 4: Update aggregate provider calls to pass context**

In `AggregateAnnouncementProvider.fetch_for_security`:
```python
for source in self.raw_sources:
    try:
        raw_items = source.provider.fetch(stock_code, market, since=since)
        items.extend(...)
    except Exception as exc:
        warnings.append(_warning_message(source.name, exc, stock_code=stock_code, market=market))
```

Do the same for `AggregateNewsProvider`.

- [ ] **Step 5: Run test to verify it passes**

Run: same pytest command
Expected: PASS

## Chunk 2: Retry logic for network errors

### Task 2: Add retry logic to Eastmoney announcement adapter

**Files:**
- Modify: `backend/app/services/providers/eastmoney_announcement.py`
- Modify: `backend/tests/services/test_eastmoney_announcement.py`
- Test: `backend/tests/services/test_eastmoney_announcement.py`

- [ ] **Step 1: Write failing test for retry on timeout**

```python
def test_eastmoney_announcement_source_retries_on_timeout():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(
            200,
            json={"data": {"list": [
                {
                    "title": "Success after retry",
                    "notice_date": "2026-03-11 10:00:00",
                    "art_code": "AN001",
                }
            ]}}
        )

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert result[0].title == "Success after retry"
    assert attempt_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/services/test_eastmoney_announcement.py::test_eastmoney_announcement_source_retries_on_timeout" -v`
Expected: FAIL because retry logic doesn't exist yet

- [ ] **Step 3: Add retry logic to fetch method**

```python
import time

def fetch(
    self,
    stock_code: str,
    market: str,
    *,
    since: datetime | None = None,
) -> list[RawAnnouncement]:
    for attempt in range(2):
        try:
            response = self._client.get(
                _EASTMONEY_BASE_URL,
                params={
                    "page_size": "100",
                    "page_index": "1",
                    "stock_list": f"{market}{stock_code}",
                },
            )
            response.raise_for_status()
            payload = response.json()

            # existing parsing logic...
            return items

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == 0:
                time.sleep(1)
                continue
            raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: same pytest command
Expected: PASS

- [ ] **Step 5: Add test for non-retryable errors**

```python
def test_eastmoney_announcement_source_does_not_retry_parse_errors():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        return httpx.Response(200, json={"unexpected": []})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match="payload missing data.list"):
        source.fetch("600519", "sh")

    assert attempt_count == 1
```

Run and verify it passes.

### Task 3: Add retry logic to remaining adapters

**Files:**
- Modify: `backend/app/services/providers/sina_announcement.py`
- Modify: `backend/app/services/providers/eastmoney_news.py`
- Modify: `backend/app/services/providers/sina_news.py`
- Modify: `backend/tests/services/test_sina_announcement.py`
- Modify: `backend/tests/services/test_eastmoney_news.py`
- Modify: `backend/tests/services/test_sina_news.py`

- [ ] **Step 1: Add retry tests for Sina announcement**

Similar to Task 2 Step 1, but for `SinaAnnouncementSource`.

- [ ] **Step 2: Add retry logic to Sina announcement fetch**

Similar to Task 2 Step 3.

- [ ] **Step 3: Run Sina announcement retry tests**

Expected: PASS

- [ ] **Step 4: Add retry tests for Eastmoney news**

Similar pattern.

- [ ] **Step 5: Add retry logic to Eastmoney news fetch**

Similar pattern.

- [ ] **Step 6: Run Eastmoney news retry tests**

Expected: PASS

- [ ] **Step 7: Add retry tests for Sina news**

Similar pattern.

- [ ] **Step 8: Add retry logic to Sina news fetch**

Similar pattern.

- [ ] **Step 9: Run Sina news retry tests**

Expected: PASS

## Chunk 3: Payload tolerance and quality warnings

### Task 4: Add payload tolerance to Eastmoney announcement adapter

**Files:**
- Modify: `backend/app/services/providers/eastmoney_announcement.py`
- Modify: `backend/tests/services/test_eastmoney_announcement.py`

- [ ] **Step 1: Write test for missing optional fields**

```python
def test_eastmoney_announcement_source_tolerates_missing_summary():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": {
                    "list": [
                        {
                            "title": "No summary item",
                            "notice_date": "2026-03-11 10:00:00",
                            "art_code": "AN001",
                            # summary is missing
                        }
                    ]
                }
            },
        )
    )

    source = EastmoneyAnnouncementSource(transport=transport)
    result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert result[0].summary is None
```

- [ ] **Step 2: Run test to verify current behavior**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/services/test_eastmoney_announcement.py::test_eastmoney_announcement_source_tolerates_missing_summary" -v`
Expected: Should already PASS (current implementation uses `_optional_str`)

- [ ] **Step 3: Write test for clearer required field errors**

```python
def test_eastmoney_announcement_source_clear_error_for_missing_title():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": {
                    "list": [
                        {
                            # title is missing
                            "notice_date": "2026-03-11 10:00:00",
                            "art_code": "AN001",
                        }
                    ]
                }
            },
        )
    )

    source = EastmoneyAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match="row 0.*missing title"):
        source.fetch("600519", "sh")
```

- [ ] **Step 4: Update error messages to include row index**

In `_require_str`:
```python
def _require_str(row: dict[str, object], key: str, *, row_index: int = 0) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Eastmoney announcement row {row_index} missing {key}")
    return value.strip()
```

Update calls in the parsing loop to pass `row_index`.

- [ ] **Step 5: Run test to verify it passes**

Run: same pytest command
Expected: PASS

### Task 5: Add payload tolerance to remaining adapters

**Files:**
- Modify: `backend/app/services/providers/sina_announcement.py`
- Modify: `backend/app/services/providers/eastmoney_news.py`
- Modify: `backend/app/services/providers/sina_news.py`
- Modify: `backend/tests/services/test_sina_announcement.py`
- Modify: `backend/tests/services/test_eastmoney_news.py`
- Modify: `backend/tests/services/test_sina_news.py`

- [ ] **Step 1: Add payload tolerance tests for Sina announcement**

Similar to Task 4.

- [ ] **Step 2: Update Sina announcement error messages with row context**

Similar pattern.

- [ ] **Step 3: Run Sina announcement tolerance tests**

Expected: PASS

- [ ] **Step 4: Add payload tolerance tests for Eastmoney news**

Similar pattern.

- [ ] **Step 5: Update Eastmoney news error messages with row context**

Similar pattern.

- [ ] **Step 6: Run Eastmoney news tolerance tests**

Expected: PASS

- [ ] **Step 7: Add payload tolerance tests for Sina news**

Similar pattern.

- [ ] **Step 8: Update Sina news error messages with row context**

Similar pattern.

- [ ] **Step 9: Run Sina news tolerance tests**

Expected: PASS

## Chunk 4: Pagination support

### Task 6: Add pagination to Eastmoney announcement adapter

**Files:**
- Modify: `backend/app/services/providers/eastmoney_announcement.py`
- Modify: `backend/tests/services/test_eastmoney_announcement.py`

- [ ] **Step 1: Write test for multi-page fetching**

```python
def test_eastmoney_announcement_source_fetches_multiple_pages():
    page_count = 0

    def mock_handler(request):
        nonlocal page_count
        page_count += 1
        page_index = int(request.url.params.get("page_index", "1"))

        if page_index == 1:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": f"Page 1 item {i}", "notice_date": "2026-03-11 10:00:00", "art_code": f"AN{i}"}
                    for i in range(50)
                ]}}
            )
        elif page_index == 2:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": f"Page 2 item {i}", "notice_date": "2026-03-11 09:00:00", "art_code": f"AN{i+50}"}
                    for i in range(50)
                ]}}
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh", max_pages=2)

    assert len(result) == 100
    assert page_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/services/test_eastmoney_announcement.py::test_eastmoney_announcement_source_fetches_multiple_pages" -v`
Expected: FAIL because max_pages parameter doesn't exist yet

- [ ] **Step 3: Add pagination logic to fetch method**

```python
def fetch(
    self,
    stock_code: str,
    market: str,
    *,
    since: datetime | None = None,
    max_pages: int = 3,
) -> list[RawAnnouncement]:
    all_items: list[RawAnnouncement] = []

    for page in range(1, max_pages + 1):
        for attempt in range(2):
            try:
                response = self._client.get(
                    _EASTMONEY_BASE_URL,
                    params={
                        "page_size": "50",
                        "page_index": str(page),
                        "stock_list": f"{market}{stock_code}",
                    },
                )
                response.raise_for_status()
                payload = response.json()

                rows = payload.get("data", {}).get("list") if isinstance(payload, dict) else None
                if not isinstance(rows, list):
                    raise ValueError("Eastmoney announcement payload missing data.list")

                if not rows:
                    break

                page_items = self._parse_rows(rows, since=since)
                all_items.extend(page_items)
                break

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise
        else:
            continue

        if not rows:
            break

    return all_items
```

Extract row parsing into `_parse_rows` helper.

- [ ] **Step 4: Run test to verify it passes**

Run: same pytest command
Expected: PASS

- [ ] **Step 5: Add test for max_pages warning**

```python
def test_eastmoney_announcement_source_warns_when_max_pages_reached():
    # Mock handler that always returns full pages
    # Verify warning is logged when page == max_pages and page is full
    pass
```

Note: This will be verified through logging tests in Task 8.

### Task 7: Add pagination to remaining adapters

**Files:**
- Modify: `backend/app/services/providers/sina_announcement.py`
- Modify: `backend/app/services/providers/eastmoney_news.py`
- Modify: `backend/app/services/providers/sina_news.py`
- Modify: `backend/tests/services/test_sina_announcement.py`
- Modify: `backend/tests/services/test_eastmoney_news.py`
- Modify: `backend/tests/services/test_sina_news.py`

- [ ] **Step 1: Add pagination tests for Sina announcement**

Note: Sina announcement uses HTML scraping, pagination may not apply. If the source doesn't support pagination, document this and skip.

- [ ] **Step 2: Add pagination to Sina announcement if applicable**

- [ ] **Step 3: Add pagination tests for Eastmoney news**

Similar to Task 6.

- [ ] **Step 4: Add pagination logic to Eastmoney news**

Similar pattern.

- [ ] **Step 5: Run Eastmoney news pagination tests**

Expected: PASS

- [ ] **Step 6: Add pagination tests for Sina news**

Similar pattern.

- [ ] **Step 7: Add pagination logic to Sina news**

Similar pattern.

- [ ] **Step 8: Run Sina news pagination tests**

Expected: PASS

## Chunk 5: Diagnostic logging

### Task 8: Add diagnostic logging to all adapters

**Files:**
- Modify: `backend/app/services/providers/eastmoney_announcement.py`
- Modify: `backend/app/services/providers/sina_announcement.py`
- Modify: `backend/app/services/providers/eastmoney_news.py`
- Modify: `backend/app/services/providers/sina_news.py`
- Modify: `backend/tests/services/test_eastmoney_announcement.py`
- Modify: `backend/tests/services/test_sina_announcement.py`
- Modify: `backend/tests/services/test_eastmoney_news.py`
- Modify: `backend/tests/services/test_sina_news.py`

- [ ] **Step 1: Write test for successful fetch logging**

```python
import logging
from unittest.mock import patch

def test_eastmoney_announcement_source_logs_successful_fetch(caplog):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"data": {"list": [
                {"title": "Item", "notice_date": "2026-03-11 10:00:00", "art_code": "AN001"}
            ]}}
        )
    )

    source = EastmoneyAnnouncementSource(transport=transport)

    with caplog.at_level(logging.INFO):
        result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert any("Provider fetch completed" in record.message for record in caplog.records)
    assert any("sh:600519" in record.message for record in caplog.records)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/services/test_eastmoney_announcement.py::test_eastmoney_announcement_source_logs_successful_fetch" -v`
Expected: FAIL because logging doesn't exist yet

- [ ] **Step 3: Add logging to Eastmoney announcement fetch**

```python
import logging
import time

logger = logging.getLogger(__name__)

def fetch(
    self,
    stock_code: str,
    market: str,
    *,
    since: datetime | None = None,
    max_pages: int = 3,
) -> list[RawAnnouncement]:
    start_time = time.time()

    try:
        all_items = []
        raw_count = 0

        # existing pagination logic...
        # track raw_count as total items before since filtering

        filtered_items = [item for item in all_items if since is None or item.published_at >= since]

        elapsed = time.time() - start_time
        logger.info(
            "Provider fetch completed: source=%s stock=%s:%s elapsed=%.2fs raw_count=%d filtered_count=%d",
            self.__class__.__name__,
            market,
            stock_code,
            elapsed,
            raw_count,
            len(filtered_items),
        )

        return filtered_items

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

- [ ] **Step 4: Run test to verify it passes**

Run: same pytest command
Expected: PASS

- [ ] **Step 5: Add logging tests for remaining adapters**

Similar tests for Sina announcement, Eastmoney news, Sina news.

- [ ] **Step 6: Add logging to remaining adapters**

Similar pattern for all three.

- [ ] **Step 7: Run all logging tests**

Expected: PASS

## Chunk 6: Verification and progress sync

### Task 9: Run full hardening verification and update workflow state

**Files:**
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: all modified test files

- [ ] **Step 1: Run the full hardening backend verification suite**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/services/test_eastmoney_announcement.py" "backend/tests/services/test_sina_announcement.py" "backend/tests/services/test_eastmoney_news.py" "backend/tests/services/test_sina_news.py" "backend/tests/services/test_real_source_aggregate_providers.py" -q`
Expected: All tests PASS

- [ ] **Step 2: Record stable hardening decisions**

Add to `memory/decisions.md`:

```md
### Real source hardening v1
- Real source adapters retry network/timeout errors once with 1-second delay.
- Reason: improves reliability for transient network issues without excessive delay.
- Error messages include source name, stock code, market, and exception type.
- Reason: makes debugging production issues much easier.
- Adapters support pagination up to 3 pages (configurable via max_pages parameter).
- Reason: ensures comprehensive data retrieval while limiting resource usage.
- Diagnostic logging records request statistics (elapsed time, record counts) at INFO level.
- Reason: provides observability for production monitoring without requiring external dependencies.
```

- [ ] **Step 3: Update progress for the next likely slice**

Update `memory/progress.md`:
- Current Focus: real source hardening v1 completed
- Last Completed: add hardening summary
- Next Step: suggest either production deployment preparation or next product module (holdings management)

## Final Notes
- Keep all changes backward compatible
- Default max_pages=3 can be overridden by callers if needed
- Logging uses standard Python logging, no configuration required
- All tests use mocked HTTP responses, no real network calls
