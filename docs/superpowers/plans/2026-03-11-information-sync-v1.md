# Information Sync v1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manually triggered single-stock sync flow so the stock detail page can sync announcements and news into the local database and refresh the displayed information.

**Architecture:** Keep reading and syncing separate. Add backend/data-layer sync services plus `POST /api/stocks/{security_id}/sync`, then add one frontend action on the stock detail page that triggers sync, displays sync state, and refreshes the detail data. Use small provider interfaces so the first version can work with deterministic seeded/test inputs before later real-source expansion.

**Tech Stack:** Python 3.12, SQLModel/SQLAlchemy, FastAPI, React, TypeScript, pytest, Vitest.

---

## File Structure

### Existing files to modify
- Modify: `backend/app/db/models/announcement.py`
- Modify: `backend/app/db/models/news_item.py`
- Modify: `backend/app/db/repositories/announcement_repository.py`
- Modify: `backend/app/db/repositories/news_repository.py`
- Modify: `backend/app/db/repositories/__init__.py`
- Modify: `backend/app/api/stocks.py`
- Modify: `backend/app/schemas/stock_detail.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `frontend/src/pages/StockDetailPage.tsx`
- Modify: `frontend/src/pages/StockDetailPage.test.tsx`
- Modify: `frontend/src/api/stocks.ts`
- Modify: `frontend/src/types/watchlist.ts`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`

### New backend files
- Create: `backend/app/services/stock_sync.py`
- Create: `backend/app/services/providers/__init__.py`
- Create: `backend/app/services/providers/announcement_provider.py`
- Create: `backend/app/services/providers/news_provider.py`
- Create: `backend/tests/db/test_announcement_upsert_repository.py`
- Create: `backend/tests/db/test_news_upsert_repository.py`
- Create: `backend/tests/services/test_stock_sync_service.py`
- Create: `backend/tests/api/test_stock_sync_api.py`

### Optional seed/support files if needed
- Create: `backend/app/db/services/seed_information_sync_demo.py`
- Create: `backend/tests/db/test_seed_information_sync_demo.py`

## Chunk 1: Data-Layer Upsert Support and Sync Service

### Task 1: Add announcement/news upsert behavior and sync service tests

**Files:**
- Modify: `backend/app/db/models/announcement.py`
- Modify: `backend/app/db/models/news_item.py`
- Modify: `backend/app/db/repositories/announcement_repository.py`
- Modify: `backend/app/db/repositories/news_repository.py`
- Create: `backend/tests/db/test_announcement_upsert_repository.py`
- Create: `backend/tests/db/test_news_upsert_repository.py`
- Create: `backend/app/services/stock_sync.py`
- Create: `backend/app/services/providers/__init__.py`
- Create: `backend/app/services/providers/announcement_provider.py`
- Create: `backend/app/services/providers/news_provider.py`
- Create: `backend/tests/services/test_stock_sync_service.py`
- Test: repository + service test files

- [ ] **Step 1: Write failing repository tests for incremental upsert behavior**

```python
def test_announcement_repository_upserts_without_duplicates(session, seeded_security): ...
def test_news_repository_upserts_without_duplicates(session, seeded_security): ...
```

- [ ] **Step 2: Run the repository tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_announcement_upsert_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_news_upsert_repository.py" -q`
Expected: FAIL because upsert methods do not exist yet

- [ ] **Step 3: Implement minimal upsert methods and uniqueness rules**

```python
class AnnouncementRepository:
    def upsert_many(self, security_id: int, items: list[AnnouncementInput]) -> int: ...

class NewsRepository:
    def upsert_many(self, security_id: int, items: list[NewsInput]) -> int: ...
```

- [ ] **Step 4: Write the failing sync service tests**

```python
def test_stock_sync_service_syncs_announcements_and_news(session, seeded_security): ...
def test_stock_sync_service_returns_warning_on_partial_failure(session, seeded_security): ...
```

- [ ] **Step 5: Run the sync service tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_stock_sync_service.py" -q`
Expected: FAIL with missing service/provider modules

- [ ] **Step 6: Implement provider protocols and stock sync service**

```python
class StockSyncService:
    def sync_stock(self, security_id: int) -> StockSyncResult: ...
```

- [ ] **Step 7: Re-run repository and service tests**

Run: the pytest commands above
Expected: PASS

## Chunk 2: Backend Sync API

### Task 2: Add `POST /api/stocks/{security_id}/sync`

**Files:**
- Modify: `backend/app/api/stocks.py`
- Modify: `backend/app/schemas/stock_detail.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/tests/api/test_stock_sync_api.py`
- Test: `backend/tests/api/test_stock_sync_api.py`

- [ ] **Step 1: Write the failing stock sync API test**

```python
def test_post_stock_sync_returns_sync_summary(client, session, seeded_security): ...
def test_post_stock_sync_returns_404_for_missing_security(client): ...
```

- [ ] **Step 2: Run the API test to verify it fails**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_api.py" -q`
Expected: FAIL because the route does not exist yet

- [ ] **Step 3: Implement sync response schema and POST endpoint**

```python
@router.post("/{security_id}/sync", response_model=StockSyncResponse)
def sync_stock_detail(...): ...
```

- [ ] **Step 4: Re-run the sync API test**

Run: same pytest command
Expected: PASS

## Chunk 3: Frontend Sync Trigger and Refresh

### Task 3: Add the detail-page sync action and refresh flow

**Files:**
- Modify: `frontend/src/api/stocks.ts`
- Modify: `frontend/src/types/watchlist.ts`
- Modify: `frontend/src/pages/StockDetailPage.tsx`
- Modify: `frontend/src/pages/StockDetailPage.test.tsx`
- Test: `frontend/src/pages/StockDetailPage.test.tsx`

- [ ] **Step 1: Extend the failing detail page test for sync behavior**

```tsx
expect(await screen.findByRole('button', { name: /sync announcements\/news/i })).toBeInTheDocument()
```

- [ ] **Step 2: Run the detail page test to verify it fails before sync UI implementation**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx`
Expected: FAIL because sync UI is missing

- [ ] **Step 3: Implement frontend sync client call**

```ts
export async function syncStockDetail(securityId: number): Promise<StockSyncResponse> { ... }
```

- [ ] **Step 4: Implement sync button, loading state, success/error messaging, and detail refresh**

```tsx
// sync button
// syncing state
// success/error feedback
// re-fetch detail after successful sync
```

- [ ] **Step 5: Re-run the detail page test**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx`
Expected: PASS

## Chunk 4: Cross-Layer Verification and Sync-State Doc Update

### Task 4: Run sync feature verification and sync docs

**Files:**
- Modify: `docs/modules/backend.md`
- Modify: `docs/modules/frontend.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: backend sync tests + frontend detail sync tests

- [ ] **Step 1: Run the information-sync automated checks**

Run:
- `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_announcement_upsert_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_news_upsert_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_stock_sync_service.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_api.py" -q`
- `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx`

Expected: all pass

- [ ] **Step 2: Record stable sync decisions if confirmed**

Add to `memory/decisions.md`:

```md
- 2026-03-11: Information sync v1 uses `POST /api/stocks/{security_id}/sync` for manual single-stock sync.
- 2026-03-11: Stock detail reads and sync writes remain separate interfaces.
```

- [ ] **Step 3: Update progress for the next recommended slice**

Set `memory/progress.md` to the next likely product direction after sync v1.

## Final Notes
- Keep this phase focused on manual single-stock sync only.
- Do not add batch sync or schedulers in this implementation.
- Use simple provider/test doubles first; real-source expansion can follow in a later slice.
