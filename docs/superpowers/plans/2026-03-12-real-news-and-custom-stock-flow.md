# Real News Sync and Custom Stock Flow Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore real news sync with a reliable provider, let users add custom stocks by market/code when local search misses, and strengthen stock detail presentation around the existing watchlist → detail → sync flow.

**Architecture:** Keep the current split between watchlist APIs, stock detail read APIs, and explicit stock sync writes. Add a dedicated backend lookup/create path for custom market+code addition, keep aggregate provider wiring for sync, and replace broken real-news adapters with a verified working implementation. Extend the frontend search flow to offer custom add as a fallback while reusing the current watchlist refresh and stock detail navigation patterns.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, httpx, pytest, React, TypeScript, Vitest, Testing Library.

---

## File Structure

### Existing files to modify
- Modify: `backend/app/api/watchlist.py`
- Modify: `backend/app/api/stocks.py`
- Modify: `backend/app/db/repositories/security_repository.py`
- Modify: `backend/app/db/repositories/watchlist_view_repository.py`
- Modify: `backend/app/db/repositories/stock_detail_repository.py`
- Modify: `backend/app/schemas/security.py`
- Modify: `backend/app/schemas/watchlist.py`
- Modify: `backend/app/schemas/stock_detail.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/services/__init__.py`
- Modify: `backend/app/services/providers/__init__.py`
- Modify: `backend/app/services/providers/aggregate_providers.py`
- Modify: `backend/app/services/providers/news_provider.py`
- Modify: `backend/app/services/providers/raw_types.py`
- Modify: `backend/tests/api/test_search_securities_api.py`
- Modify: `backend/tests/api/test_watchlist_mutation_api.py`
- Modify: `backend/tests/api/test_watchlist_list_api.py`
- Modify: `backend/tests/api/test_stock_detail_api.py`
- Modify: `backend/tests/api/test_stock_sync_api.py`
- Modify: `backend/tests/services/test_real_source_aggregate_providers.py`
- Modify: `backend/tests/services/test_stock_sync_real_sources.py`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/api/watchlist.ts`
- Modify: `frontend/src/components/SearchBox.tsx`
- Modify: `frontend/src/components/SearchBox.test.tsx`
- Modify: `frontend/src/components/StockHeader.tsx`
- Modify: `frontend/src/components/WatchlistTable.tsx`
- Modify: `frontend/src/components/WatchlistTable.test.tsx`
- Modify: `frontend/src/pages/StockDetailPage.tsx`
- Modify: `frontend/src/pages/StockDetailPage.test.tsx`
- Modify: `frontend/src/types/watchlist.ts`
- Modify: `docs/modules/frontend.md`
- Modify: `docs/02-module-registry.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`

### New files to create
- Create: `backend/app/services/security_lookup.py`
- Create: `backend/app/services/providers/eastmoney_security_lookup.py`
- Create: `backend/app/services/providers/ifeng_news.py`
- Create: `backend/tests/services/test_security_lookup_service.py`
- Create: `backend/tests/services/test_eastmoney_security_lookup.py`
- Create: `backend/tests/services/test_ifeng_news.py`

### Responsibility map
- `security_lookup.py`: backend service that normalizes market/code, fetches upstream stock metadata, and upserts a `Security`
- `eastmoney_security_lookup.py`: real upstream lookup adapter for stock identity metadata used by custom add
- `ifeng_news.py`: stable real news adapter replacing degraded broken news source behavior
- `watchlist.py` + `watchlist` schemas/tests: API contract for local search plus custom add-and-track flow
- `stocks.py` + stock detail/sync schemas/tests: keep sync/detail wiring but expose stronger stock identity/sync metadata in responses
- frontend `SearchBox` + `App` + API/types/tests: offer custom add fallback and preserve watchlist refresh behavior
- frontend `StockDetailPage`/`StockHeader`/`WatchlistTable`: improve presentation of core stock information without changing page structure

## Chunk 1: Custom stock lookup and creation backend

### Task 1: Add a real stock lookup adapter for market+code

**Files:**
- Create: `backend/app/services/providers/eastmoney_security_lookup.py`
- Modify: `backend/app/services/providers/raw_types.py`
- Modify: `backend/app/services/providers/__init__.py`
- Test: `backend/tests/services/test_eastmoney_security_lookup.py`

- [ ] **Step 1: Write the failing lookup adapter tests**

```python
from app.services.providers.eastmoney_security_lookup import EastmoneySecurityLookupSource


def test_eastmoney_security_lookup_source_maps_real_payload_to_security_seed():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "QuotationCodeTable": {
                    "Data": [
                        {
                            "Code": "600519",
                            "Name": "Kweichow Moutai",
                            "SecurityTypeName": "A股",
                            "MktNum": "1",
                        }
                    ]
                }
            },
        )
    )

    source = EastmoneySecurityLookupSource(transport=transport)

    result = source.fetch("SH", "600519")

    assert result.market == "SH"
    assert result.code == "600519"
    assert result.name == "Kweichow Moutai"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_eastmoney_security_lookup.py::test_eastmoney_security_lookup_source_maps_real_payload_to_security_seed" -v`
Expected: FAIL because the adapter file and supporting raw type do not exist yet.

- [ ] **Step 3: Add the minimal raw lookup type and adapter implementation**

```python
# backend/app/services/providers/raw_types.py
@dataclass(frozen=True)
class RawSecurityLookup:
    market: str
    code: str
    name: str
    industry: str | None = None
    status: str = "active"
```

```python
# backend/app/services/providers/eastmoney_security_lookup.py
class EastmoneySecurityLookupSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self, market: str, code: str) -> RawSecurityLookup:
        normalized_market = market.upper().strip()
        normalized_code = code.strip()
        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                "https://searchapi.eastmoney.com/api/suggest/get",
                params={"input": normalized_code, "type": "14"},
            )
            response.raise_for_status()
            payload = response.json()

        rows = payload.get("QuotationCodeTable", {}).get("Data")
        if not isinstance(rows, list) or not rows:
            raise ValueError("security lookup returned no matches")

        row = next(
            (
                item for item in rows
                if isinstance(item, dict)
                and item.get("Code") == normalized_code
                and _normalize_market(item.get("MktNum")) == normalized_market
            ),
            None,
        )
        if row is None:
            raise ValueError(f"security lookup did not match {normalized_market}:{normalized_code}")

        return RawSecurityLookup(
            market=normalized_market,
            code=normalized_code,
            name=_require_text(row, "Name"),
            industry=_optional_text(row.get("SecurityTypeName")),
        )
```

- [ ] **Step 4: Run the focused lookup adapter tests**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_eastmoney_security_lookup.py" -q`
Expected: PASS.

- [ ] **Step 5: Commit the adapter slice**

```bash
git add backend/app/services/providers/raw_types.py backend/app/services/providers/__init__.py backend/app/services/providers/eastmoney_security_lookup.py backend/tests/services/test_eastmoney_security_lookup.py
git commit -m "feat: add real stock lookup adapter"
```

### Task 2: Add a security lookup service that fetches and upserts a custom stock

**Files:**
- Create: `backend/app/services/security_lookup.py`
- Modify: `backend/app/services/__init__.py`
- Modify: `backend/app/db/repositories/security_repository.py`
- Test: `backend/tests/services/test_security_lookup_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
def test_security_lookup_service_creates_missing_security_from_lookup_source(session):
    repository = SecurityRepository(session)
    service = SecurityLookupService(
        repository=repository,
        source=StubLookupSource(
            RawSecurityLookup(
                market="SZ",
                code="002594",
                name="BYD",
                industry="Auto",
            )
        ),
    )

    security = service.lookup_or_create("sz", "002594")

    assert security.market == "SZ"
    assert security.code == "002594"
    assert security.name == "BYD"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_security_lookup_service.py::test_security_lookup_service_creates_missing_security_from_lookup_source" -v`
Expected: FAIL because the service does not exist yet.

- [ ] **Step 3: Implement the minimal service and repository helper**

```python
# backend/app/db/repositories/security_repository.py
    def get_by_market_code(self, market: str, code: str) -> Security | None:
        normalized_market = market.strip().upper()
        normalized_code = code.strip()
        statement = select(Security).where(
            Security.market == normalized_market,
            Security.code == normalized_code,
        )
        return self.session.exec(statement).first()
```

```python
# backend/app/services/security_lookup.py
class SecurityLookupService:
    def __init__(self, *, repository: SecurityRepository, source: SecurityLookupSource):
        self.repository = repository
        self.source = source

    def lookup_or_create(self, market: str, code: str) -> Security:
        normalized_market = market.strip().upper()
        normalized_code = code.strip()
        existing = self.repository.get_by_market_code(normalized_market, normalized_code)
        if existing is not None:
            return existing

        raw_security = self.source.fetch(normalized_market, normalized_code)
        persisted = self.repository.upsert_many(
            [
                Security(
                    market=raw_security.market,
                    code=raw_security.code,
                    name=raw_security.name,
                    industry=raw_security.industry,
                    status=raw_security.status,
                )
            ]
        )
        return persisted[0]
```

- [ ] **Step 4: Run the focused service tests**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_security_lookup_service.py" -q`
Expected: PASS.

- [ ] **Step 5: Commit the service slice**

```bash
git add backend/app/services/security_lookup.py backend/app/services/__init__.py backend/app/db/repositories/security_repository.py backend/tests/services/test_security_lookup_service.py
git commit -m "feat: add security lookup create service"
```

### Task 3: Add a custom watchlist add endpoint using market+code lookup

**Files:**
- Modify: `backend/app/api/watchlist.py`
- Modify: `backend/app/schemas/watchlist.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/tests/api/test_watchlist_mutation_api.py`
- Modify: `backend/tests/api/test_search_securities_api.py`

- [ ] **Step 1: Write the failing API tests**

```python
def test_add_watchlist_item_by_market_code_creates_missing_security_and_returns_it(...):
    response = client.post(
        "/api/watchlist/items/custom",
        json={"market": "SZ", "code": "002594"},
    )

    assert response.status_code == 200
    assert response.json()["security"]["market"] == "SZ"
    assert response.json()["security"]["code"] == "002594"
```

```python
def test_search_securities_returns_empty_list_and_preserves_custom_add_path(client):
    response = client.get("/api/watchlist/securities/search", params={"query": "002594"})
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run the focused API tests to verify they fail**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_watchlist_mutation_api.py::test_add_watchlist_item_by_market_code_creates_missing_security_and_returns_it" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_watchlist_mutation_api.py::test_add_watchlist_item_by_market_code_returns_422_for_invalid_market" -v`
Expected: FAIL because the endpoint and request/response schemas do not exist yet.

- [ ] **Step 3: Add the endpoint and schemas with minimal behavior**

```python
# backend/app/schemas/watchlist.py
class WatchlistCustomAddRequest(SQLModel):
    market: str
    code: str

class WatchlistCustomAddResponse(SQLModel):
    security_id: int
    security: SecuritySearchResult
```

```python
# backend/app/api/watchlist.py
@router.post("/items/custom", response_model=WatchlistCustomAddResponse)
def add_watchlist_item_by_market_code(
    payload: WatchlistCustomAddRequest,
    session: Session = Depends(get_session),
) -> WatchlistCustomAddResponse:
    if payload.market.strip().upper() not in {"SH", "SZ"}:
        raise HTTPException(status_code=422, detail="market must be SH or SZ")

    security_repository = SecurityRepository(session)
    lookup_service = SecurityLookupService(
        repository=security_repository,
        source=EastmoneySecurityLookupSource(),
    )
    security = lookup_service.lookup_or_create(payload.market, payload.code)

    watchlist_repository = WatchlistRepository(session)
    watchlist_repository.add(security.id)
    return WatchlistCustomAddResponse(
        security_id=security.id,
        security=SecuritySearchResult.from_model(security),
    )
```

- [ ] **Step 4: Run the focused watchlist API tests**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_watchlist_mutation_api.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_search_securities_api.py" -q`
Expected: PASS.

- [ ] **Step 5: Commit the custom add API slice**

```bash
git add backend/app/api/watchlist.py backend/app/schemas/watchlist.py backend/app/schemas/__init__.py backend/tests/api/test_watchlist_mutation_api.py backend/tests/api/test_search_securities_api.py
git commit -m "feat: add custom watchlist stock creation api"
```

## Chunk 2: Restore real news sync with a reliable source

### Task 4: Add a reliable real news adapter

**Files:**
- Create: `backend/app/services/providers/ifeng_news.py`
- Modify: `backend/app/services/providers/__init__.py`
- Modify: `backend/app/services/providers/news_provider.py`
- Test: `backend/tests/services/test_ifeng_news.py`

- [ ] **Step 1: Write the failing real news adapter tests**

```python
from app.services.providers.ifeng_news import IfengNewsSource


def test_ifeng_news_source_maps_html_rows_to_raw_news_items():
    html = """
    <html><body>
      <div class=\"news-list\">
        <a href=\"https://finance.ifeng.com/c/8abc\">Moutai gains on demand recovery</a>
        <span>2026-03-12 09:30</span>
      </div>
    </body></html>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))
    source = IfengNewsSource(transport=transport)

    result = source.fetch("600519", "SH")

    assert result[0].title == "Moutai gains on demand recovery"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_ifeng_news.py::test_ifeng_news_source_maps_html_rows_to_raw_news_items" -v`
Expected: FAIL because the adapter does not exist yet.

- [ ] **Step 3: Implement the minimal reliable news adapter**

```python
# backend/app/services/providers/ifeng_news.py
class IfengNewsSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
        max_pages: int = 3,
    ) -> list[RawNewsItem]:
        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                "https://finance.ifeng.com/lib/stock/search",
                params={"code": f"{market.lower()}{stock_code}"},
            )
            response.raise_for_status()

        rows = _extract_rows(response.text)
        items = [_parse_row(row, index=index) for index, row in enumerate(rows)]
        return [item for item in items if since is None or item.published_at >= since]
```

Keep parsing minimal and explicit. Use a small HTML parser or regex-free DOM-like extraction pattern that matches the verified markup.

- [ ] **Step 4: Run the focused real news adapter tests**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/services/test_ifeng_news.py" -q`
Expected: PASS.

- [ ] **Step 5: Commit the reliable adapter slice**

```bash
git add backend/app/services/providers/ifeng_news.py backend/app/services/providers/__init__.py backend/app/services/providers/news_provider.py backend/tests/services/test_ifeng_news.py
git commit -m "feat: add reliable real news adapter"
```

### Task 5: Rewire aggregate news sync to use the reliable source

**Files:**
- Modify: `backend/app/api/stocks.py`
- Modify: `backend/tests/api/test_stock_sync_api.py`
- Modify: `backend/tests/services/test_real_source_aggregate_providers.py`
- Modify: `backend/tests/services/test_stock_sync_real_sources.py`

- [ ] **Step 1: Write the failing provider wiring tests**

```python
def test_get_stock_sync_service_builds_reliable_real_news_provider(session):
    service = get_stock_sync_service(...)
    assert [adapter.name for adapter in service.news_provider.raw_sources] == ["ifeng"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_api.py::test_get_stock_sync_service_builds_reliable_real_news_provider" -v`
Expected: FAIL because the sync service still wires `eastmoney` and `sina` for news.

- [ ] **Step 3: Update the aggregate news provider wiring**

```python
# backend/app/api/stocks.py

def get_aggregate_news_provider() -> AggregateNewsProvider:
    return AggregateNewsProvider(
        raw_sources=[
            RawNewsSourceAdapter("ifeng", IfengNewsSource()),
        ]
    )
```

Also update service-level tests so stock metadata and warnings still flow through unchanged.

- [ ] **Step 4: Run the focused news sync wiring tests**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_api.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_real_source_aggregate_providers.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_stock_sync_real_sources.py" -q`
Expected: PASS.

- [ ] **Step 5: Commit the sync wiring slice**

```bash
git add backend/app/api/stocks.py backend/tests/api/test_stock_sync_api.py backend/tests/services/test_real_source_aggregate_providers.py backend/tests/services/test_stock_sync_real_sources.py
git commit -m "feat: restore real news sync with reliable provider"
```

## Chunk 3: Strengthen stock info presentation contracts

### Task 6: Extend backend stock detail and watchlist rows with clearer stock identity fields

**Files:**
- Modify: `backend/app/db/repositories/watchlist_view_repository.py`
- Modify: `backend/app/db/repositories/stock_detail_repository.py`
- Modify: `backend/app/schemas/stock_detail.py`
- Modify: `backend/app/schemas/watchlist.py`
- Modify: `backend/tests/api/test_watchlist_list_api.py`
- Modify: `backend/tests/api/test_stock_detail_api.py`

- [ ] **Step 1: Write the failing API response tests**

```python
def test_list_watchlist_items_returns_market_with_each_row(...):
    response = client.get("/api/watchlist/items")
    assert response.json()[0]["market"] == "SZ"
```

```python
def test_get_stock_detail_returns_stock_identity_and_sync_metadata(...):
    response = client.get(f"/api/stocks/{seeded_security.id}")
    assert response.json()["security"]["market"] == "SZ"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_watchlist_list_api.py::test_list_watchlist_items_returns_market_with_each_row" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_detail_api.py::test_get_stock_detail_returns_security_with_price_context_announcements_and_news" -v`
Expected: FAIL because watchlist rows do not currently include `market`.

- [ ] **Step 3: Add the minimal repository and schema fields**

```python
# backend/app/db/repositories/watchlist_view_repository.py
@dataclass(frozen=True)
class WatchlistRow:
    security_id: int
    market: str
    code: str
    name: str
    industry: Optional[str]
    ...
```

```python
# backend/app/schemas/watchlist.py
class WatchlistListRow(SQLModel):
    security_id: int
    market: str
    code: str
    name: str
    ...
```

Keep `StockDetailSecurityResponse` aligned with the repository model and add only fields that are already backed by data.

- [ ] **Step 4: Run the focused stock identity API tests**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_watchlist_list_api.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_detail_api.py" -q`
Expected: PASS.

- [ ] **Step 5: Commit the stock identity contract slice**

```bash
git add backend/app/db/repositories/watchlist_view_repository.py backend/app/db/repositories/stock_detail_repository.py backend/app/schemas/watchlist.py backend/app/schemas/stock_detail.py backend/tests/api/test_watchlist_list_api.py backend/tests/api/test_stock_detail_api.py
git commit -m "feat: extend stock identity presentation contracts"
```

## Chunk 4: Frontend custom add flow and detail presentation

### Task 7: Add custom market+code fallback to the search flow

**Files:**
- Modify: `frontend/src/api/watchlist.ts`
- Modify: `frontend/src/components/SearchBox.tsx`
- Modify: `frontend/src/components/SearchBox.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/types/watchlist.ts`

- [ ] **Step 1: Write the failing frontend tests**

```tsx
it('offers custom add when search returns no matches and adds by market and code', async () => {
  render(<SearchBox onAdd={vi.fn()} onAddCustom={vi.fn()} />)

  fireEvent.change(screen.getByLabelText(/search securities/i), {
    target: { value: '002594' },
  })
  fireEvent.click(screen.getByRole('button', { name: /search/i }))

  expect(await screen.findByRole('button', { name: /add sz:002594/i })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- --run frontend/src/components/SearchBox.test.tsx frontend/src/App.test.tsx`
Expected: FAIL because the custom add callback and UI do not exist yet.

- [ ] **Step 3: Add the minimal custom add client and UI flow**

```ts
// frontend/src/api/watchlist.ts
export async function addCustomWatchlistItem(market: string, code: string) {
  const response = await fetch('/api/watchlist/items/custom', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ market, code }),
  })
  if (!response.ok) {
    throw new Error('Unable to add that custom stock right now.')
  }
  return (await response.json()) as { security_id: number; security: SecuritySearchResult }
}
```

```tsx
// frontend/src/components/SearchBox.tsx
interface SearchBoxProps {
  onAdd: (securityId: number) => void
  onAddCustom: (market: string, code: string) => void
}
```

Render a compact fallback section when `hasSearched && results.length === 0`, with a market selector defaulting from the query pattern and a button that calls `onAddCustom`.

- [ ] **Step 4: Run the focused frontend search tests**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- --run frontend/src/components/SearchBox.test.tsx frontend/src/App.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit the custom add frontend slice**

```bash
git add frontend/src/api/watchlist.ts frontend/src/components/SearchBox.tsx frontend/src/components/SearchBox.test.tsx frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/types/watchlist.ts
git commit -m "feat: add custom stock fallback in search flow"
```

### Task 8: Improve watchlist and stock detail presentation for core stock information

**Files:**
- Modify: `frontend/src/components/WatchlistTable.tsx`
- Modify: `frontend/src/components/WatchlistTable.test.tsx`
- Modify: `frontend/src/components/StockHeader.tsx`
- Modify: `frontend/src/pages/StockDetailPage.tsx`
- Modify: `frontend/src/pages/StockDetailPage.test.tsx`

- [ ] **Step 1: Write the failing presentation tests**

```tsx
it('renders market and code together in the watchlist table', () => {
  render(<WatchlistTable ... />)
  expect(screen.getByText('SZ:000001')).toBeInTheDocument()
})
```

```tsx
it('renders a stronger stock identity header with market, code, industry, and status', () => {
  render(<StockDetailPage detail={detailData} viewState="ready" onBack={vi.fn()} />)
  expect(screen.getByText('SZ:000001')).toBeInTheDocument()
  expect(screen.getByText(/banking/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- --run frontend/src/components/WatchlistTable.test.tsx frontend/src/pages/StockDetailPage.test.tsx`
Expected: FAIL because the UI does not yet render the strengthened combined identity presentation.

- [ ] **Step 3: Implement the minimal presentation updates**

```tsx
// frontend/src/components/WatchlistTable.tsx
<td>{`${item.market}:${item.code}`}</td>
```

```tsx
// frontend/src/components/StockHeader.tsx
<div className="stock-detail-meta" aria-label="Stock identity and status">
  <span>{`${security.market}:${security.code}`}</span>
  <span>{security.status}</span>
</div>
```

Also adjust `StockDetailPage` copy so it reflects a real tracked stock workspace rather than a placeholder shell.

- [ ] **Step 4: Run the focused presentation tests**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- --run frontend/src/components/WatchlistTable.test.tsx frontend/src/pages/StockDetailPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit the presentation slice**

```bash
git add frontend/src/components/WatchlistTable.tsx frontend/src/components/WatchlistTable.test.tsx frontend/src/components/StockHeader.tsx frontend/src/pages/StockDetailPage.tsx frontend/src/pages/StockDetailPage.test.tsx
git commit -m "feat: improve stock info presentation"
```

## Chunk 5: End-to-end verification and workflow sync

### Task 9: Run full verification and update project state

**Files:**
- Modify: `docs/modules/frontend.md`
- Modify: `docs/02-module-registry.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`

- [ ] **Step 1: Run the full backend verification for this slice**

Run: `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_search_securities_api.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_watchlist_mutation_api.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_watchlist_list_api.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_detail_api.py" "/Users/peter/Desktop/Investment Board/backend/tests/api/test_stock_sync_api.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_security_lookup_service.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_eastmoney_security_lookup.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_ifeng_news.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_real_source_aggregate_providers.py" "/Users/peter/Desktop/Investment Board/backend/tests/services/test_stock_sync_real_sources.py" -q`
Expected: PASS.

- [ ] **Step 2: Run the full frontend verification for this slice**

Run: `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend" -- --run`
Expected: PASS.

- [ ] **Step 3: Run the user-facing local acceptance entrypoint**

Run: `"/Users/peter/Desktop/Investment Board/scripts/run_all.sh" --seed`
Expected: backend and frontend start cleanly with the new custom add and real news sync behavior available for manual acceptance.

- [ ] **Step 4: Update stable decisions and progress state**

Add/update in `memory/decisions.md`:

```md
### Custom stock add and real news restoration
- Custom stock addition uses fetch-then-create by `market + code`; users do not create empty local securities by manual freeform name entry.
- Reason: keeps data quality acceptable while still supporting codes outside the seeded local dataset.
- Real news sync prefers one verified reliable provider over multiple fragile providers.
- Reason: the product goal is dependable sync results, not source-count maximization.
- Watchlist and detail presentation emphasize essential identity fields (`market`, `code`, `name`, `industry`, `status`) plus explicit sync results.
- Reason: this is the smallest UI change that makes tracked stocks understandable during review.
```

Update `memory/progress.md` and `docs/modules/frontend.md` with what was actually implemented and verified. If frontend is the active module, keep `docs/02-module-registry.md` aligned with its status.

- [ ] **Step 5: Commit the verification and state sync slice**

```bash
git add docs/modules/frontend.md docs/02-module-registry.md memory/progress.md memory/decisions.md
git commit -m "docs: record custom stock and real news slice"
```

## Final Notes
- Follow @superpowers:test-driven-development strictly: every code change starts with a focused failing test.
- Keep the custom add path separate from the existing `POST /api/watchlist/items` endpoint to avoid overloading old behavior.
- Do not keep the broken degraded news endpoints wired once the reliable provider is in place.
- If the chosen real upstream lookup or news source proves unstable during implementation, stop and swap to another verified source at the provider layer without changing the API contracts above.
