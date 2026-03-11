# Stock Detail v1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the second product slice after the watchlist MVP: a stock detail page entered from the watchlist, backed by a single aggregated detail API and real detail-oriented data entities.

**Architecture:** Extend the existing watchlist stack incrementally in module order: first add detail-oriented entities and repositories in the data layer, then expose a single `GET /api/stocks/{security_id}` backend aggregation endpoint, then add a frontend detail page reached from the watchlist list. Keep the detail response resilient to partial data by returning empty lists or nulls for missing sub-sections instead of failing the whole page.

**Tech Stack:** Python 3.12, SQLModel/SQLAlchemy, FastAPI, React, Vite, TypeScript, pytest, Vitest.

---

## File Structure

### Existing files to modify
- Modify: `backend/app/db/models/__init__.py`
- Modify: `backend/app/db/repositories/__init__.py`
- Modify: `backend/app/api/watchlist.py` — only to add detail navigation support in responses if required by the chosen frontend route shape.
- Modify: `backend/app/api/__init__.py` if needed for route module exports.
- Modify: `backend/app/schemas/__init__.py`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/watchlist.ts`
- Modify: `frontend/src/types/watchlist.ts`
- Modify: `frontend/src/components/WatchlistTable.tsx`
- Modify: `docs/modules/data-layer.md`, `docs/modules/backend.md`, `docs/modules/frontend.md`
- Modify: `docs/02-module-registry.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`

### New data-layer files
- Create: `backend/app/db/models/price_bar_daily.py`
- Create: `backend/app/db/models/announcement.py`
- Create: `backend/app/db/models/news_item.py`
- Create: `backend/app/db/repositories/price_context_repository.py`
- Create: `backend/app/db/repositories/announcement_repository.py`
- Create: `backend/app/db/repositories/news_repository.py`
- Create: `backend/app/db/repositories/stock_detail_repository.py`
- Create: `backend/tests/db/test_price_context_repository.py`
- Create: `backend/tests/db/test_announcement_repository.py`
- Create: `backend/tests/db/test_news_repository.py`
- Create: `backend/tests/db/test_stock_detail_repository.py`

### New backend files
- Create: `backend/app/api/stocks.py`
- Create: `backend/app/schemas/stock_detail.py`
- Create: `backend/tests/api/test_stock_detail_api.py`

### New frontend files
- Create: `frontend/src/api/stocks.ts`
- Create: `frontend/src/pages/StockDetailPage.tsx`
- Create: `frontend/src/pages/StockDetailPage.test.tsx`
- Create: `frontend/src/components/StockHeader.tsx`
- Create: `frontend/src/components/QuoteSummary.tsx`
- Create: `frontend/src/components/PriceContextPanel.tsx`
- Create: `frontend/src/components/AnnouncementList.tsx`
- Create: `frontend/src/components/NewsList.tsx`

### Optional scripts/integration files if needed
- Create or modify only if real detail data seeding is required for local acceptance:
  - `backend/app/db/services/seed_stock_detail_demo.py`
  - `backend/tests/db/test_seed_stock_detail_demo.py`

## Chunk 1: Data-Layer Foundation for Stock Detail

### Task 1: Add detail data models for price context, announcements, and news

**Files:**
- Create: `backend/app/db/models/price_bar_daily.py`
- Create: `backend/app/db/models/announcement.py`
- Create: `backend/app/db/models/news_item.py`
- Modify: `backend/app/db/models/__init__.py`
- Modify: `backend/app/db/session.py`
- Create: `backend/tests/db/test_stock_detail_models.py`
- Test: `backend/tests/db/test_stock_detail_models.py`

- [ ] **Step 1: Write the failing schema test for the three new detail tables**

```python
from sqlalchemy import inspect

from app.core.settings import Settings
from app.db.session import create_db_and_tables, make_engine


def test_create_db_and_tables_creates_stock_detail_tables(tmp_path):
    db_path = tmp_path / "stock-detail.db"
    engine = make_engine(Settings(database_url=f"sqlite:///{db_path}"))

    create_db_and_tables(engine)

    table_names = set(inspect(engine).get_table_names())
    assert {"price_bars_daily", "announcements", "news_items"}.issubset(table_names)
```

- [ ] **Step 2: Run the schema test to verify it fails before implementation**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_stock_detail_models.py" -q`
Expected: FAIL because the detail models do not exist yet

- [ ] **Step 3: Implement `PriceBarDaily`, `Announcement`, and `NewsItem` with minimal indexed fields**

```python
class PriceBarDaily(SQLModel, table=True):
    __tablename__ = "price_bars_daily"
    security_id: int = Field(foreign_key="securities.id", index=True)
    trade_date: date = Field(index=True)
    close_price: Decimal = Field(...)
```

```python
class Announcement(SQLModel, table=True):
    __tablename__ = "announcements"
    security_id: int = Field(foreign_key="securities.id", index=True)
    title: str
    published_at: datetime = Field(index=True)
    source: str
    url: str
```

```python
class NewsItem(SQLModel, table=True):
    __tablename__ = "news_items"
    security_id: int = Field(foreign_key="securities.id", index=True)
    title: str
    published_at: datetime = Field(index=True)
    source: str
    url: str
```

- [ ] **Step 4: Export the models and re-run the schema test**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_stock_detail_models.py" -q`
Expected: PASS

### Task 2: Implement data-layer repositories for detail queries and aggregation

**Files:**
- Create: `backend/app/db/repositories/price_context_repository.py`
- Create: `backend/app/db/repositories/announcement_repository.py`
- Create: `backend/app/db/repositories/news_repository.py`
- Create: `backend/app/db/repositories/stock_detail_repository.py`
- Modify: `backend/app/db/repositories/__init__.py`
- Create: `backend/tests/db/test_price_context_repository.py`
- Create: `backend/tests/db/test_announcement_repository.py`
- Create: `backend/tests/db/test_news_repository.py`
- Create: `backend/tests/db/test_stock_detail_repository.py`
- Test: the four new db test files

- [ ] **Step 1: Write the failing repository tests**

```python
def test_price_context_repository_returns_recent_rows_in_desc_date_order(session, seeded_security):
    ...


def test_announcement_repository_returns_recent_announcements(session, seeded_security):
    ...


def test_news_repository_returns_recent_news(session, seeded_security):
    ...


def test_stock_detail_repository_returns_null_or_empty_sections_when_data_is_missing(session, seeded_security):
    ...
```

- [ ] **Step 2: Run the repository tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_price_context_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_announcement_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_news_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_stock_detail_repository.py" -q`
Expected: FAIL with missing repository modules

- [ ] **Step 3: Implement focused repositories plus one aggregate repository**

```python
class PriceContextRepository:
    def list_recent(self, security_id: int, limit: int = 30) -> list[PriceBarDaily]: ...

class AnnouncementRepository:
    def list_recent(self, security_id: int, limit: int = 20) -> list[Announcement]: ...

class NewsRepository:
    def list_recent(self, security_id: int, limit: int = 20) -> list[NewsItem]: ...

class StockDetailRepository:
    def get_detail(self, security_id: int) -> StockDetailRecord | None: ...
```

- [ ] **Step 4: Re-run the repository tests**

Run: same pytest command as Step 2
Expected: PASS

## Chunk 2: Backend Stock Detail API

### Task 3: Add the stock detail backend schema and API endpoint

**Files:**
- Create: `backend/app/schemas/stock_detail.py`
- Create: `backend/app/api/stocks.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/api/test_stock_detail_api.py`
- Test: `backend/tests/api/test_stock_detail_api.py`

- [ ] **Step 1: Write the failing detail API test**

```python
def test_get_stock_detail_returns_aggregated_sections(client, session, seeded_security):
    response = client.get(f"/api/stocks/{seeded_security.id}")
    assert response.status_code == 200
    assert "security" in response.json()
    assert "price_context" in response.json()
    assert "announcements" in response.json()
    assert "news" in response.json()
```

- [ ] **Step 2: Run the detail API test to verify it fails before implementation**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_detail_api.py" -q`
Expected: FAIL with missing route or schema errors

- [ ] **Step 3: Implement stock detail response schemas**

```python
class StockDetailResponse(SQLModel):
    security: SecurityDetailSection
    latest_quote: LatestQuoteSection | None
    price_context: list[PriceContextRow]
    announcements: list[AnnouncementRow]
    news: list[NewsRow]
```

- [ ] **Step 4: Implement `GET /api/stocks/{security_id}`**

```python
@router.get("/api/stocks/{security_id}", response_model=StockDetailResponse)
def get_stock_detail(...):
    detail = StockDetailRepository(session).get_detail(security_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="stock detail not found")
    return StockDetailResponse.model_validate(detail)
```

- [ ] **Step 5: Re-run the detail API test**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_detail_api.py" -q`
Expected: PASS

## Chunk 3: Frontend Detail Navigation and Page Rendering

### Task 4: Add detail-page navigation from the watchlist list

**Files:**
- Modify: `frontend/src/types/watchlist.ts`
- Modify: `frontend/src/components/WatchlistTable.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/StockDetailPage.tsx`
- Create: `frontend/src/pages/StockDetailPage.test.tsx`
- Test: `frontend/src/pages/StockDetailPage.test.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing frontend detail-page test**

```tsx
test("opens stock detail page when a watchlist row is clicked", async () => {
  ...
  expect(await screen.findByRole("heading", { name: /Ping An Bank/i })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run the frontend detail tests to verify they fail**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx src/App.test.tsx`
Expected: FAIL with missing detail page or navigation behavior

- [ ] **Step 3: Implement minimal page-level navigation state in `App.tsx`**

```tsx
// local page mode: watchlist list vs stock detail
// selectedSecurityId state
```

- [ ] **Step 4: Implement `StockDetailPage` shell with loading/error/404/empty-section states**

```tsx
// render header, latest quote summary, price context section, announcements section, news section
```

- [ ] **Step 5: Re-run the frontend detail tests**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx src/App.test.tsx`
Expected: PASS

### Task 5: Add frontend stock detail API client and render the detail sections

**Files:**
- Create: `frontend/src/api/stocks.ts`
- Create: `frontend/src/components/StockHeader.tsx`
- Create: `frontend/src/components/QuoteSummary.tsx`
- Create: `frontend/src/components/PriceContextPanel.tsx`
- Create: `frontend/src/components/AnnouncementList.tsx`
- Create: `frontend/src/components/NewsList.tsx`
- Modify: `frontend/src/pages/StockDetailPage.tsx`
- Modify: `frontend/src/types/watchlist.ts`
- Test: `frontend/src/pages/StockDetailPage.test.tsx`

- [ ] **Step 1: Write or extend the failing detail page test for successful detail rendering**

```tsx
expect(await screen.findByText(/latest price/i)).toBeInTheDocument()
expect(screen.getByText(/announcements/i)).toBeInTheDocument()
expect(screen.getByText(/news/i)).toBeInTheDocument()
```

- [ ] **Step 2: Run the detail page test to verify it fails before implementation**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx`
Expected: FAIL with missing API client or missing rendered sections

- [ ] **Step 3: Implement the detail API client and frontend types**

```ts
export async function fetchStockDetail(securityId: number): Promise<StockDetailResponse> {
  const response = await fetch(`/api/stocks/${securityId}`)
  ...
}
```

- [ ] **Step 4: Implement focused detail subcomponents and wire them into the page**

```tsx
<StockHeader ... />
<QuoteSummary ... />
<PriceContextPanel ... />
<AnnouncementList ... />
<NewsList ... />
```

- [ ] **Step 5: Re-run the detail page tests**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx`
Expected: PASS

## Chunk 4: Cross-Layer Verification and Doc Sync

### Task 6: Run the stock detail verification suite and sync module docs

**Files:**
- Modify: `docs/modules/data-layer.md`
- Modify: `docs/modules/backend.md`
- Modify: `docs/modules/frontend.md`
- Modify: `docs/02-module-registry.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: new backend db/api tests and frontend detail tests

- [ ] **Step 1: Run the stock detail automated checks**

Run:
- `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_stock_detail_models.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_price_context_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_announcement_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_news_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_stock_detail_repository.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_detail_api.py" -q`
- `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- src/pages/StockDetailPage.test.tsx src/App.test.tsx`

Expected: all pass

- [ ] **Step 2: Record stable decisions for stock detail v1 if confirmed**

Add to `memory/decisions.md`:

```md
- 2026-03-11: Stock detail v1 uses a single aggregated backend endpoint at `GET /api/stocks/{security_id}`.
- 2026-03-11: Stock detail v1 enters only from the watchlist list; direct code-route entry is deferred.
```

- [ ] **Step 3: Update the module docs with actual implementation scope and verification evidence**

Document:
- new data-layer entities and repositories
- backend detail API
- frontend detail page and state handling

- [ ] **Step 4: Sync progress for the next module or acceptance step**

Update `memory/progress.md` with the next recommended step after stock detail v1.

## Final Notes
- Keep this phase focused on stock detail v1 only; do not drift into AI analysis, positions, or complex charts.
- If real news / announcement sourcing requires a separate sync slice, stop after schema/API/UI support and create a follow-up plan rather than expanding silently.
