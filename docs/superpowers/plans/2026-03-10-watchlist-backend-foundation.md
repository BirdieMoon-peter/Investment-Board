# Watchlist MVP Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend API layer for the watchlist MVP so the frontend can search securities, add/remove watchlist items, and fetch the watchlist list view from the completed data-layer module.

**Architecture:** Extend the existing `backend/` Python workspace with a minimal FastAPI application, Pydantic/SQLModel response schemas, and thin route handlers that delegate all persistence work to the completed repositories. Keep the backend slice narrowly scoped to four HTTP endpoints and one app factory so the next frontend module can consume a stable JSON contract without introducing unrelated features.

**Tech Stack:** Python 3.12, FastAPI, SQLModel/SQLAlchemy, SQLite, pytest.

---

## File Structure

### Existing files to modify
- Modify: `backend/pyproject.toml` — add FastAPI and HTTP test dependencies.
- Modify: `backend/app/core/settings.py` — extend settings only as needed for backend app bootstrap.
- Modify: `backend/app/db/session.py` — expose a small dependency/helper usable by route handlers.
- Modify: `backend/app/db/repositories/security_repository.py` — only if small backend-facing lookup helpers are required by route/service code.
- Modify: `docs/modules/backend.md` — record concrete backend files, verification commands, and review evidence.
- Modify: `docs/02-module-registry.md` — move `backend` from `doing` to `review`, then to `done` after review passes.
- Modify: `memory/progress.md` — keep execution state and next handoff step in sync.
- Modify: `memory/decisions.md` — record any stable backend contract decisions confirmed during implementation.

### New backend application files
- Create: `backend/app/main.py` — FastAPI app factory and route registration.
- Create: `backend/app/api/__init__.py` — package marker for API modules.
- Create: `backend/app/api/dependencies.py` — request-scoped database session dependency.
- Create: `backend/app/api/watchlist.py` — four watchlist MVP endpoints only.
- Create: `backend/app/schemas/__init__.py` — schema exports.
- Create: `backend/app/schemas/security.py` — search response schema for securities.
- Create: `backend/app/schemas/watchlist.py` — request/response schemas for add/remove/list APIs.

### New test files
- Create: `backend/tests/api/test_search_securities_api.py` — verifies search endpoint behavior and empty results.
- Create: `backend/tests/api/test_watchlist_mutation_api.py` — verifies add/remove watchlist APIs, duplicate add handling, and invalid security failures.
- Create: `backend/tests/api/test_watchlist_list_api.py` — verifies watchlist list response fields and missing-quote behavior.
- Create: `backend/tests/api/conftest.py` — FastAPI test client fixture built on the existing in-memory DB setup.

### Explicitly deferred files
- Do not create auth, users, or session-management files.
- Do not create stock detail endpoints.
- Do not create AI, portfolio, or event/news API files.
- Do not create background task runners or external fetch integrations in this slice.

## Chunk 1: App Bootstrap and Search API

### Task 1: Add FastAPI app bootstrap and shared API test client

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/dependencies.py`
- Create: `backend/tests/api/conftest.py`
- Create: `backend/tests/api/test_search_securities_api.py`
- Test: `backend/tests/api/test_search_securities_api.py`

- [ ] **Step 1: Add the missing backend web dependencies to `backend/pyproject.toml`**

```toml
[project]
dependencies = [
  "fastapi>=0.115,<0.116",
  "sqlmodel>=0.0.24,<0.1.0",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.28,<0.29",
  "pytest>=8.0,<9.0",
]
```

- [ ] **Step 2: Write the failing API search test before creating the app**

```python
from fastapi.testclient import TestClient


def test_search_securities_returns_empty_list_when_no_match(client: TestClient):
    response = client.get("/api/watchlist/securities/search", params={"query": "no-match"})

    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 3: Install the updated backend package with web-test dependencies**

Run: `python3 -m pip install -e "backend[dev]"`
Expected: output includes `fastapi` and `httpx`

- [ ] **Step 4: Run the API search test to verify it fails before implementation**

Run: `python3 -m pytest "backend/tests/api/test_search_securities_api.py" -q`
Expected: FAIL with an import error for `app.main` or missing `client` fixture

- [ ] **Step 5: Implement the minimal FastAPI app and DB dependency**

```python
from fastapi import FastAPI

from app.api.watchlist import router as watchlist_router


def create_app() -> FastAPI:
    app = FastAPI(title="Investment Board Backend")
    app.include_router(watchlist_router, prefix="/api/watchlist", tags=["watchlist"])
    return app


app = create_app()
```

```python
from collections.abc import Generator

from sqlmodel import Session

from app.core.settings import Settings
from app.db.session import make_engine


def get_session() -> Generator[Session, None, None]:
    engine = make_engine(Settings())
    with Session(engine) as session:
        yield session
```

- [ ] **Step 6: Implement the shared test client fixture with dependency override support**

```python
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_session
from app.main import create_app


@pytest.fixture(name="client")
def client_fixture(session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: iter([session])
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
```

- [ ] **Step 7: Re-run the API search test and verify it now fails because the route itself does not exist yet**

Run: `python3 -m pytest "backend/tests/api/test_search_securities_api.py" -q`
Expected: FAIL with `404` or router import failure for the missing watchlist route module

### Task 2: Implement the search securities endpoint and response schema

**Files:**
- Create: `backend/app/api/watchlist.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/security.py`
- Modify: `backend/tests/api/test_search_securities_api.py`
- Test: `backend/tests/api/test_search_securities_api.py`

- [ ] **Step 1: Extend the failing search test to seed securities and assert ordered JSON output**

```python
from app.db.models import Security


def test_search_securities_returns_active_matches_in_mvp_order(client, session):
    session.add(Security(market="SH", code="600519", name="贵州茅台", industry="白酒", status="active"))
    session.add(Security(market="SZ", code="000001", name="平安银行", industry="银行", status="active"))
    session.add(Security(market="SZ", code="300001", name="特锐德", industry="电气设备", status="inactive"))
    session.commit()

    response = client.get("/api/watchlist/securities/search", params={"query": "6005"})

    assert response.status_code == 200
    assert response.json()[0]["code"] == "600519"
    assert all(row["status"] == "active" for row in response.json())
```

- [ ] **Step 2: Run the search API test to verify it fails because the route/schema do not exist yet**

Run: `python3 -m pytest "backend/tests/api/test_search_securities_api.py" -q`
Expected: FAIL with missing route or schema errors

- [ ] **Step 3: Implement the search response schema**

```python
from pydantic import BaseModel


class SecuritySearchResult(BaseModel):
    security_id: int
    market: str
    code: str
    name: str
    industry: str | None
    status: str
```

- [ ] **Step 4: Implement the search endpoint as a thin wrapper over `SecurityRepository.search()`**

```python
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.dependencies import get_session
from app.db.repositories import SecurityRepository
from app.schemas.security import SecuritySearchResult

router = APIRouter()


@router.get("/securities/search", response_model=list[SecuritySearchResult])
def search_securities(
    query: str = Query(min_length=1),
    session: Session = Depends(get_session),
) -> list[SecuritySearchResult]:
    rows = SecurityRepository(session).search(query)
    return [
        SecuritySearchResult(
            security_id=row.id,
            market=row.market,
            code=row.code,
            name=row.name,
            industry=row.industry,
            status=row.status,
        )
        for row in rows
    ]
```

- [ ] **Step 5: Re-run the search API tests**

Run: `python3 -m pytest "backend/tests/api/test_search_securities_api.py" -q`
Expected: PASS

## Chunk 2: Watchlist Mutation and List APIs

### Task 3: Implement the add/remove watchlist APIs with backend-specific failure handling

**Files:**
- Create: `backend/app/schemas/watchlist.py`
- Create: `backend/tests/api/test_watchlist_mutation_api.py`
- Modify: `backend/app/api/watchlist.py`
- Test: `backend/tests/api/test_watchlist_mutation_api.py`

- [ ] **Step 1: Write the failing add/remove API tests**

```python
def test_add_watchlist_item_creates_or_returns_existing_item(client, session, seeded_security):
    first = client.post("/api/watchlist/items", json={"security_id": seeded_security.id})
    second = client.post("/api/watchlist/items", json={"security_id": seeded_security.id})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["security_id"] == second.json()["security_id"]


def test_remove_watchlist_item_returns_404_for_missing_security(client):
    response = client.delete("/api/watchlist/items/999")

    assert response.status_code == 404
```

- [ ] **Step 2: Run the mutation API tests to verify they fail before implementation**

Run: `python3 -m pytest "backend/tests/api/test_watchlist_mutation_api.py" -q`
Expected: FAIL with missing route/schema errors

- [ ] **Step 3: Implement add/remove request and response schemas**

```python
from pydantic import BaseModel


class WatchlistAddRequest(BaseModel):
    security_id: int


class WatchlistItemResponse(BaseModel):
    security_id: int


class WatchlistRemoveResponse(BaseModel):
    removed: bool
    security_id: int
```

- [ ] **Step 4: Implement `POST /api/watchlist/items` with explicit unknown-security handling**

```python
from fastapi import HTTPException

from app.db.repositories import SecurityRepository, WatchlistRepository


@router.post("/items", response_model=WatchlistItemResponse)
def add_watchlist_item(payload: WatchlistAddRequest, session: Session = Depends(get_session)) -> WatchlistItemResponse:
    security = SecurityRepository(session).list_by_market_code([])  # replace with actual security existence lookup helper
    existing_security = session.get(Security, payload.security_id)
    if existing_security is None:
        raise HTTPException(status_code=404, detail="Security not found")
    item = WatchlistRepository(session).add(payload.security_id)
    return WatchlistItemResponse(security_id=item.security_id)
```

- [ ] **Step 5: Implement `DELETE /api/watchlist/items/{security_id}`**

```python
@router.delete("/items/{security_id}", response_model=WatchlistRemoveResponse)
def remove_watchlist_item(security_id: int, session: Session = Depends(get_session)) -> WatchlistRemoveResponse:
    removed = WatchlistRepository(session).remove_by_security_id(security_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return WatchlistRemoveResponse(removed=True, security_id=security_id)
```

- [ ] **Step 6: Re-run the mutation API tests**

Run: `python3 -m pytest "backend/tests/api/test_watchlist_mutation_api.py" -q`
Expected: PASS

### Task 4: Implement the watchlist list API and output schema

**Files:**
- Create: `backend/tests/api/test_watchlist_list_api.py`
- Modify: `backend/app/schemas/watchlist.py`
- Modify: `backend/app/api/watchlist.py`
- Test: `backend/tests/api/test_watchlist_list_api.py`

- [ ] **Step 1: Write the failing watchlist list API test**

```python
from datetime import datetime

from app.db.models import QuoteSnapshot
from app.db.repositories import WatchlistRepository


def test_list_watchlist_returns_joined_security_and_quote_fields(client, session, seeded_security):
    WatchlistRepository(session).add(seeded_security.id)
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price="10.5000",
            change_amount="0.5000",
            change_percent="5.0000",
            snapshot_time=datetime(2026, 3, 10, 9, 35),
        )
    )
    session.commit()

    response = client.get("/api/watchlist/items")

    assert response.status_code == 200
    assert response.json()[0]["code"] == seeded_security.code
    assert response.json()[0]["last_price"] == "10.5000"
```

- [ ] **Step 2: Run the watchlist list API test to verify it fails before implementation**

Run: `python3 -m pytest "backend/tests/api/test_watchlist_list_api.py" -q`
Expected: FAIL with missing route/schema errors

- [ ] **Step 3: Implement the watchlist list response schema**

```python
class WatchlistListRow(BaseModel):
    security_id: int
    code: str
    name: str
    industry: str | None
    last_price: str | None
    change_percent: str | None
    snapshot_time: datetime | None
```

- [ ] **Step 4: Implement `GET /api/watchlist/items` using `WatchlistViewRepository.list_rows()`**

```python
from app.db.repositories import WatchlistViewRepository


@router.get("/items", response_model=list[WatchlistListRow])
def list_watchlist_items(session: Session = Depends(get_session)) -> list[WatchlistListRow]:
    rows = WatchlistViewRepository(session).list_rows()
    return [
        WatchlistListRow(
            security_id=row.security_id,
            code=row.code,
            name=row.name,
            industry=row.industry,
            last_price=str(row.last_price) if row.last_price is not None else None,
            change_percent=str(row.change_percent) if row.change_percent is not None else None,
            snapshot_time=row.snapshot_time,
        )
        for row in rows
    ]
```

- [ ] **Step 5: Re-run the watchlist list API test**

Run: `python3 -m pytest "backend/tests/api/test_watchlist_list_api.py" -q`
Expected: PASS

## Chunk 3: Full Backend Verification and Review-State Sync

### Task 5: Run backend verification and sync review-state docs

**Files:**
- Modify: `docs/modules/backend.md`
- Modify: `docs/02-module-registry.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: `backend/tests/api/*.py`

- [ ] **Step 1: Run the full backend API test suite**

Run: `python3 -m pytest "backend/tests/api" -q`
Expected: all tests PASS

- [ ] **Step 2: Record stable backend decisions**

Add to `memory/decisions.md`:

```md
- 2026-03-10: The watchlist MVP backend uses FastAPI with thin route handlers over repository classes.
- 2026-03-10: Backend watchlist responses expose `security_id` as the mutation and deletion key.
- 2026-03-10: Missing securities and missing watchlist rows return `404` from backend endpoints.
```

- [ ] **Step 3: Update the backend module doc with actual implementation scope and verification commands**

Add or update these points in `docs/modules/backend.md`:

```md
## Verification
- `python3 -m pytest "backend/tests/api" -q`
- search endpoint verified for ordered active-only matches and empty results
- add/remove endpoints verified for idempotent add and `404` failure paths
- watchlist list endpoint verified for joined security + latest quote output and missing-quote behavior
```

- [ ] **Step 4: Move the active module into review and update progress memory**

Update:
- `docs/02-module-registry.md`: set `backend` to `review`
- `memory/progress.md`: set the next step to frontend planning for search input and watchlist list UI

- [ ] **Step 5: Run `@superpowers:requesting-code-review` for the completed backend module**

Expected: review findings are recorded and required fixes are applied before completion claims

- [ ] **Step 6: Run `@superpowers:verification-before-completion` before moving the module to done**

Expected: evidence-based verification confirms the backend module is ready for completion

- [ ] **Step 7: If both review skills pass, mark the module done and record the review date**

Update:
- `docs/02-module-registry.md`: set `backend` to `done` and fill `Last Review`
- `memory/progress.md`: set the next active planning target to `frontend`

## Final Notes
- Keep all code changes scoped to the backend module; do not modify frontend UI files while executing this plan.
- If endpoint behavior suggests missing data-layer capabilities, add the minimum backend-facing helper only if it stays inside the existing data-layer contract; otherwise stop and re-plan.
- If git is initialized before execution, create one commit per chunk after the full chunk test suite passes. If git is still not initialized, skip commit steps rather than inventing git history.
