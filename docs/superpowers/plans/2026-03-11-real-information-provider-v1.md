# Real Information Provider v1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stub announcement/news providers with real multi-source aggregate providers that preserve the existing single-stock sync flow and surface partial-success warnings back to the stock detail page.

**Architecture:** Keep the current sync API and detail page interaction intact, and evolve only the provider layer plus sync result shape. Implement one adapter per source, one aggregate provider per information type, and extend the sync service to merge results, collect warnings, and return counts plus warnings without changing the overall user flow.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, pytest, React, TypeScript, Vitest.

---

## File Structure

### Existing files to modify
- Modify: `backend/app/services/providers/announcement_provider.py`
- Modify: `backend/app/services/providers/news_provider.py`
- Modify: `backend/app/services/providers/__init__.py`
- Modify: `backend/app/services/stock_sync.py`
- Modify: `backend/app/api/stocks.py`
- Modify: `backend/app/schemas/stock_detail.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `frontend/src/api/stocks.ts`
- Modify: `frontend/src/types/watchlist.ts`
- Modify: `frontend/src/pages/StockDetailPage.tsx`
- Modify: `frontend/src/pages/StockDetailPage.test.tsx`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`

### New backend files
- Create: `backend/app/services/providers/announcement_source_a.py`
- Create: `backend/app/services/providers/announcement_source_b.py`
- Create: `backend/app/services/providers/news_source_a.py`
- Create: `backend/app/services/providers/news_source_b.py`
- Create: `backend/app/services/providers/aggregated_announcements.py`
- Create: `backend/app/services/providers/aggregated_news.py`
- Create: `backend/tests/services/test_aggregated_announcement_provider.py`
- Create: `backend/tests/services/test_aggregated_news_provider.py`
- Create: `backend/tests/services/test_stock_sync_service_warnings.py`
- Create: `backend/tests/api/test_stock_sync_warning_api.py`

### Optional support files if needed
- Create: `backend/tests/services/provider_fixtures.py`

## Chunk 1: Aggregate Provider Layer

### Task 1: Implement multi-source aggregate providers for announcements and news

**Files:**
- Create: `backend/app/services/providers/announcement_source_a.py`
- Create: `backend/app/services/providers/announcement_source_b.py`
- Create: `backend/app/services/providers/news_source_a.py`
- Create: `backend/app/services/providers/news_source_b.py`
- Create: `backend/app/services/providers/aggregated_announcements.py`
- Create: `backend/app/services/providers/aggregated_news.py`
- Modify: `backend/app/services/providers/__init__.py`
- Create: `backend/tests/services/test_aggregated_announcement_provider.py`
- Create: `backend/tests/services/test_aggregated_news_provider.py`
- Test: the two new provider test files

- [ ] **Step 1: Write failing tests for announcement aggregate provider**

```python
def test_aggregated_announcement_provider_merges_multiple_sources_without_duplicates(): ...
def test_aggregated_announcement_provider_returns_warnings_for_failed_sources(): ...
```

- [ ] **Step 2: Write failing tests for news aggregate provider**

```python
def test_aggregated_news_provider_merges_multiple_sources_without_duplicates(): ...
def test_aggregated_news_provider_returns_warnings_for_failed_sources(): ...
```

- [ ] **Step 3: Run the aggregate provider tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_aggregated_announcement_provider.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_aggregated_news_provider.py" -q`
Expected: FAIL because aggregate providers do not exist yet

- [ ] **Step 4: Implement source adapters and aggregate providers**

```python
class AggregatedAnnouncementProvider:
    def fetch_for_security(self, security_id: int, *, since=None) -> ProviderBatchResult[Announcement]: ...
```

```python
class AggregatedNewsProvider:
    def fetch_for_security(self, security_id: int, *, since=None) -> ProviderBatchResult[NewsItem]: ...
```

- [ ] **Step 5: Re-run the aggregate provider tests**

Run: same pytest command
Expected: PASS

## Chunk 2: Sync Service and API Warning Propagation

### Task 2: Propagate warning-rich partial-success results through sync service and API

**Files:**
- Modify: `backend/app/services/stock_sync.py`
- Modify: `backend/app/api/stocks.py`
- Modify: `backend/app/schemas/stock_detail.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/tests/services/test_stock_sync_service_warnings.py`
- Create: `backend/tests/api/test_stock_sync_warning_api.py`
- Test: service + API warning test files

- [ ] **Step 1: Write the failing sync-service warning tests**

```python
def test_stock_sync_service_returns_partial_success_with_warnings(session, seeded_security): ...
def test_stock_sync_service_fails_only_when_all_sources_fail(session, seeded_security): ...
```

- [ ] **Step 2: Write the failing sync API warning test**

```python
def test_post_stock_sync_returns_warnings_and_synced_at(client, session, seeded_security): ...
```

- [ ] **Step 3: Run the warning tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_stock_sync_service_warnings.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_warning_api.py" -q`
Expected: FAIL because warning propagation is not implemented yet

- [ ] **Step 4: Extend `StockSyncResult` and `StockSyncResponse` with warning-aware fields**

```python
class StockSyncResult:
    announcements_upserted: int
    news_items_upserted: int
    warnings: list[str]
    synced: bool
```

- [ ] **Step 5: Wire aggregate providers into the sync endpoint**

```python
def get_stock_sync_service(...):
    return StockSyncService(
        announcement_provider=AggregatedAnnouncementProvider(...),
        news_provider=AggregatedNewsProvider(...),
        ...
    )
```

- [ ] **Step 6: Re-run the warning tests**

Run: same pytest command
Expected: PASS

## Chunk 3: Frontend Warning Display

### Task 3: Show sync warnings and partial-success messaging in the detail page

**Files:**
- Modify: `frontend/src/api/stocks.ts`
- Modify: `frontend/src/types/watchlist.ts`
- Modify: `frontend/src/pages/StockDetailPage.tsx`
- Modify: `frontend/src/pages/StockDetailPage.test.tsx`
- Test: `frontend/src/pages/StockDetailPage.test.tsx`

- [ ] **Step 1: Extend the failing detail page sync test for warning display**

```tsx
expect(await screen.findByText(/1 warning/i)).toBeInTheDocument()
```

- [ ] **Step 2: Run the detail page test to verify it fails before warning UI implementation**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx`
Expected: FAIL because warning rendering is missing

- [ ] **Step 3: Extend frontend sync types for warning-aware responses**

```ts
export interface StockSyncResponse {
  security_id: number
  announcements_upserted: number
  news_items_upserted: number
  warnings: string[]
  synced: boolean
  synced_at: string
}
```

- [ ] **Step 4: Render partial-success and warning messaging in `StockDetailPage`**

```tsx
// success message includes counts
// warning block renders when warnings.length > 0
```

- [ ] **Step 5: Re-run the detail page tests**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx`
Expected: PASS

## Chunk 4: Verification and Progress Sync

### Task 4: Run real-provider verification and sync progress

**Files:**
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: provider, sync, and frontend sync tests

- [ ] **Step 1: Run the real-provider automated checks**

Run:
- `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_aggregated_announcement_provider.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_aggregated_news_provider.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_stock_sync_service_warnings.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_warning_api.py" -q`
- `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx`

Expected: all pass

- [ ] **Step 2: Record stable decisions if confirmed**

Add to `memory/decisions.md`:

```md
- 2026-03-11: Real information provider v1 uses aggregate providers with multiple source adapters per information type.
- 2026-03-11: Partial source failures surface as warnings instead of failing the entire sync by default.
```

- [ ] **Step 3: Update progress with the next likely slice**

Set `memory/progress.md` to the next recommended step after real provider v1.

## Final Notes
- Keep the current sync path manual and single-stock only.
- Prioritize merge success and warning propagation over perfect normalization.
- Avoid expanding into schedulers or batch sync in this implementation.
