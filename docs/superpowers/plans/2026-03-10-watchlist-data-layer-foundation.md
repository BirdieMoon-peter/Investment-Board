# Watchlist MVP Data-Layer Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first active module for the watchlist MVP by creating the persistent data-layer foundation for securities, watchlist membership, and latest quote snapshots.

**Architecture:** Create a new `backend/` Python workspace now, even though only the data-layer module is active, so the future backend API can land next to the persistence code without moving files later. Use SQLModel models plus repository classes around a single session module, with SQLite file persistence for the local single-user MVP while keeping schema and query patterns compatible with a later PostgreSQL migration.

**Tech Stack:** Python 3.12, SQLModel/SQLAlchemy, SQLite, pytest.

---

## File Structure

### Existing files to modify
- Modify: `docs/modules/data-layer.md` — record the concrete files, verification steps, and review evidence for the active module.
- Modify: `docs/02-module-registry.md` — move `data-layer` from `doing` to `review` and then to `done` only after review passes.
- Modify: `memory/progress.md` — keep current execution state and next handoff step in sync.
- Modify: `memory/decisions.md` — record stable implementation decisions such as SQLite-for-local-MVP and the initial backend workspace layout.

### New backend workspace files
- Create: `backend/pyproject.toml` — Python package metadata and dev dependencies.
- Create: `backend/app/__init__.py` — package marker.
- Create: `backend/app/core/__init__.py` — package marker.
- Create: `backend/app/core/settings.py` — database file path and local runtime settings.
- Create: `backend/app/db/__init__.py` — package marker.
- Create: `backend/app/db/session.py` — engine, session factory, and schema bootstrap function.
- Create: `backend/app/db/models/__init__.py` — exports data-layer models.
- Create: `backend/app/db/models/security.py` — `Security` SQLModel table.
- Create: `backend/app/db/models/watchlist_item.py` — `WatchlistItem` SQLModel table.
- Create: `backend/app/db/models/quote_snapshot.py` — `QuoteSnapshot` SQLModel table.
- Create: `backend/app/db/repositories/__init__.py` — package marker.
- Create: `backend/app/db/repositories/security_repository.py` — search and upsert for securities.
- Create: `backend/app/db/repositories/watchlist_repository.py` — add/remove/idempotency rules for watchlist items.
- Create: `backend/app/db/repositories/watchlist_view_repository.py` — join watchlist items to securities and latest quote snapshots.
- Create: `backend/app/db/services/__init__.py` — package marker.
- Create: `backend/app/db/services/bootstrap_data.py` — import normalized security and quote records into the database without external HTTP fetching.

### New test files
- Create: `backend/tests/conftest.py` — temporary database fixture and reusable sample factories.
- Create: `backend/tests/db/test_settings_and_session.py` — verifies local SQLite settings and table creation.
- Create: `backend/tests/db/test_security_repository.py` — verifies uniqueness, upsert behavior, and code/name search ordering.
- Create: `backend/tests/db/test_watchlist_repository.py` — verifies add/remove behavior and duplicate protection.
- Create: `backend/tests/db/test_watchlist_view_repository.py` — verifies latest-snapshot join logic and missing-quote handling.
- Create: `backend/tests/db/test_bootstrap_data.py` — verifies normalized bootstrap records can seed securities and quote snapshots.

### Explicitly deferred files
- Do not create any API router files yet.
- Do not create any frontend files yet.
- Do not create external fetch scripts yet.
- Do not add Alembic migrations in this slice; use `SQLModel.metadata.create_all()` for the first local MVP foundation.

## Chunk 1: Backend Workspace and Schema Foundation

### Task 1: Create the backend Python workspace and local database session

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/settings.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/session.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/db/test_settings_and_session.py`
- Test: `backend/tests/db/test_settings_and_session.py`

- [ ] **Step 1: Create the backend package metadata and dev dependencies**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "investment-board-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "sqlmodel>=0.0.22,<0.1.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0,<9.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]
```

- [ ] **Step 2: Write the failing session bootstrap test**

```python
from app.core.settings import Settings
from app.db.session import create_db_and_tables, make_engine


def test_local_settings_create_sqlite_database(tmp_path):
    db_path = tmp_path / "watchlist.db"
    settings = Settings(database_url=f"sqlite:///{db_path}")

    engine = make_engine(settings)
    create_db_and_tables(engine)

    assert db_path.exists()
```

- [ ] **Step 3: Install the backend package in editable mode with test dependencies**

Run: `python -m pip install -e "/Users/peter/Desktop/Investment Board/backend[dev]"`
Expected: output includes `investment-board-backend` and `pytest`

- [ ] **Step 4: Run the test to verify it fails before implementation**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_settings_and_session.py" -q`
Expected: FAIL with an import error for `app.core.settings` or `app.db.session`

- [ ] **Step 5: Implement the minimal settings and session bootstrap code**

```python
from dataclasses import dataclass

from sqlmodel import SQLModel, Session, create_engine


@dataclass(slots=True)
class Settings:
    database_url: str = "sqlite:///./investment_board.db"


def make_engine(settings: Settings):
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, echo=False, connect_args=connect_args)


def create_db_and_tables(engine) -> None:
    SQLModel.metadata.create_all(engine)


def make_session(engine) -> Session:
    return Session(engine)
```

- [ ] **Step 6: Create the shared pytest fixtures in `backend/tests/conftest.py`**

```python
import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.db.models import Security


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="seeded_security")
def seeded_security_fixture(session):
    security = Security(
        market="SH",
        code="600000",
        name="浦发银行",
        industry="银行",
        status="active",
    )
    session.add(security)
    session.commit()
    session.refresh(security)
    return security
```

- [ ] **Step 7: Run the session bootstrap test again**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_settings_and_session.py" -q`
Expected: PASS

### Task 2: Define the three SQLModel tables for the MVP schema

**Files:**
- Create: `backend/app/db/models/__init__.py`
- Create: `backend/app/db/models/security.py`
- Create: `backend/app/db/models/watchlist_item.py`
- Create: `backend/app/db/models/quote_snapshot.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/db/test_settings_and_session.py`
- Test: `backend/tests/db/test_settings_and_session.py`

- [ ] **Step 1: Extend the failing test so it asserts all three tables are created**

```python
from sqlalchemy import inspect


def test_create_db_and_tables_creates_watchlist_schema(tmp_path):
    db_path = tmp_path / "watchlist.db"
    settings = Settings(database_url=f"sqlite:///{db_path}")
    engine = make_engine(settings)

    create_db_and_tables(engine)

    table_names = set(inspect(engine).get_table_names())
    assert {"securities", "watchlist_items", "quote_snapshots"}.issubset(table_names)
```

- [ ] **Step 2: Run the test to verify it fails because the models do not exist yet**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_settings_and_session.py" -q`
Expected: FAIL because the expected tables are missing

- [ ] **Step 3: Implement the `Security` model with uniqueness for `(market, code)`**

```python
from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Security(SQLModel, table=True):
    __tablename__ = "securities"
    __table_args__ = (UniqueConstraint("market", "code", name="uq_security_market_code"),)

    id: int | None = Field(default=None, primary_key=True)
    market: str = Field(index=True, max_length=16)
    code: str = Field(index=True, max_length=16)
    name: str = Field(index=True, max_length=64)
    industry: str | None = Field(default=None, max_length=128)
    status: str = Field(default="active", index=True, max_length=16)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Implement the `WatchlistItem` model with unique `security_id`**

```python
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class WatchlistItem(SQLModel, table=True):
    __tablename__ = "watchlist_items"

    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key="securities.id", index=True, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 5: Implement the `QuoteSnapshot` model with indexed `snapshot_time`**

```python
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


class QuoteSnapshot(SQLModel, table=True):
    __tablename__ = "quote_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key="securities.id", index=True)
    last_price: Decimal = Field(max_digits=12, decimal_places=3)
    change_amount: Decimal = Field(max_digits=12, decimal_places=3)
    change_percent: Decimal = Field(max_digits=8, decimal_places=3)
    snapshot_time: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 6: Import the model modules from `backend/app/db/models/__init__.py` so metadata registration happens before `create_all()`**

```python
from .quote_snapshot import QuoteSnapshot
from .security import Security
from .watchlist_item import WatchlistItem
```

- [ ] **Step 7: Import `app.db.models` from `backend/app/db/session.py` before calling `SQLModel.metadata.create_all()`**

```python
from app.db import models  # noqa: F401
```

- [ ] **Step 8: Re-run the table creation test**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_settings_and_session.py" -q`
Expected: PASS

## Chunk 2: Repository Boundaries and Query Behavior

### Task 3: Implement the security repository with search and upsert behavior

**Files:**
- Create: `backend/app/db/repositories/__init__.py`
- Create: `backend/app/db/repositories/security_repository.py`
- Create: `backend/tests/db/test_security_repository.py`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/db/test_security_repository.py`

- [ ] **Step 1: Write the failing security repository tests**

```python
from sqlmodel import select

from app.db.models import Security
from app.db.repositories.security_repository import SecurityRepository


def test_upsert_security_updates_existing_market_code(session):
    repo = SecurityRepository(session)

    repo.upsert_many([
        {"market": "SZ", "code": "000001", "name": "平安银行", "industry": "银行", "status": "active"},
        {"market": "SZ", "code": "000001", "name": "平安银行", "industry": "银行", "status": "active"},
    ])

    rows = session.query(Security).all()
    assert len(rows) == 1


def test_search_returns_exact_code_before_partial_name(session):
    repo = SecurityRepository(session)
    repo.upsert_many([
        {"market": "SH", "code": "600519", "name": "贵州茅台", "industry": "白酒", "status": "active"},
        {"market": "SZ", "code": "000001", "name": "平安银行", "industry": "银行", "status": "active"},
    ])

    results = repo.search("6005")

    assert results[0].code == "600519"
    assert len(results) <= 20
```

- [ ] **Step 2: Run the repository tests to verify they fail**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_security_repository.py" -q`
Expected: FAIL with an import error for `SecurityRepository`

- [ ] **Step 3: Implement `SecurityRepository.upsert_many()` with `(market, code)` matching**

```python
from datetime import datetime, timezone

class SecurityRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(self, items: list[dict]) -> None:
        for item in items:
            existing = self.session.exec(
                select(Security).where(Security.market == item["market"], Security.code == item["code"])
            ).first()
            if existing:
                existing.name = item["name"]
                existing.industry = item.get("industry")
                existing.status = item.get("status", existing.status)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                self.session.add(Security(**item))
        self.session.commit()
```

- [ ] **Step 4: Implement `SecurityRepository.search()` with the MVP ordering and filtering rules**

```python
    def search(self, query: str, limit: int = 20) -> list[Security]:
        normalized = query.strip()
        if not normalized:
            return []

        exact_code = select(Security).where(Security.status == "active", Security.code == normalized)
        exact_name = select(Security).where(Security.status == "active", Security.name == normalized)
        code_prefix = select(Security).where(Security.status == "active", Security.code.startswith(normalized))
        name_contains = select(Security).where(Security.status == "active", Security.name.contains(normalized))

        ordered_ids: list[int] = []
        for statement in [exact_code, exact_name, code_prefix, name_contains]:
            for row in self.session.exec(statement.limit(limit)).all():
                if row.id not in ordered_ids:
                    ordered_ids.append(row.id)
        if not ordered_ids:
            return []
        rows = self.session.exec(select(Security).where(Security.id.in_(ordered_ids))).all()
        by_id = {row.id: row for row in rows}
        return [by_id[row_id] for row_id in ordered_ids][:limit]
```

- [ ] **Step 5: Run the security repository tests again**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_security_repository.py" -q`
Expected: PASS

### Task 4: Implement the watchlist repository with add/remove/idempotent behavior

**Files:**
- Create: `backend/app/db/repositories/watchlist_repository.py`
- Create: `backend/tests/db/test_watchlist_repository.py`
- Test: `backend/tests/db/test_watchlist_repository.py`

- [ ] **Step 1: Write the failing watchlist repository tests**

```python
from app.db.repositories.watchlist_repository import WatchlistRepository


def test_add_returns_existing_item_for_duplicate_security(session, seeded_security):
    repo = WatchlistRepository(session)

    first = repo.add(seeded_security.id)
    second = repo.add(seeded_security.id)

    assert first.id == second.id


def test_remove_deletes_item_by_security_id(session, seeded_security):
    repo = WatchlistRepository(session)
    repo.add(seeded_security.id)

    removed = repo.remove_by_security_id(seeded_security.id)

    assert removed is True
    assert repo.list_ids() == []
```

- [ ] **Step 2: Run the watchlist repository tests to verify they fail**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_watchlist_repository.py" -q`
Expected: FAIL with an import error for `WatchlistRepository`

- [ ] **Step 3: Implement `WatchlistRepository.add()` with idempotent duplicate handling**

```python
class WatchlistRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, security_id: int) -> WatchlistItem:
        existing = self.session.exec(
            select(WatchlistItem).where(WatchlistItem.security_id == security_id)
        ).first()
        if existing:
            return existing
        item = WatchlistItem(security_id=security_id)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item
```

- [ ] **Step 4: Implement `remove_by_security_id()` and `list_ids()`**

```python
    def remove_by_security_id(self, security_id: int) -> bool:
        existing = self.session.exec(
            select(WatchlistItem).where(WatchlistItem.security_id == security_id)
        ).first()
        if not existing:
            return False
        self.session.delete(existing)
        self.session.commit()
        return True

    def list_ids(self) -> list[int]:
        return [row.security_id for row in self.session.exec(select(WatchlistItem)).all()]
```

- [ ] **Step 5: Run the watchlist repository tests again**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_watchlist_repository.py" -q`
Expected: PASS

### Task 5: Implement the watchlist view repository for latest quote joins

**Files:**
- Create: `backend/app/db/repositories/watchlist_view_repository.py`
- Create: `backend/tests/db/test_watchlist_view_repository.py`
- Test: `backend/tests/db/test_watchlist_view_repository.py`

- [ ] **Step 1: Write the failing watchlist view tests**

```python
from datetime import datetime, timezone

from app.db.models import QuoteSnapshot
from app.db.repositories.watchlist_repository import WatchlistRepository
from app.db.repositories.watchlist_view_repository import WatchlistViewRepository


def test_list_view_returns_latest_snapshot_for_each_security(session, seeded_security):
    WatchlistRepository(session).add(seeded_security.id)
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price="12.00",
            change_amount="0.00",
            change_percent="0.00",
            snapshot_time=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        )
    )
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price="12.30",
            change_amount="0.30",
            change_percent="2.50",
            snapshot_time=datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc),
        )
    )
    session.commit()

    repo = WatchlistViewRepository(session)
    rows = repo.list_rows()

    assert rows[0].code == seeded_security.code
    assert float(rows[0].last_price) == 12.30


def test_list_view_keeps_security_when_quote_is_missing(session, seeded_security):
    WatchlistRepository(session).add(seeded_security.id)

    repo = WatchlistViewRepository(session)
    rows = repo.list_rows()

    assert rows[0].code == seeded_security.code
    assert rows[0].last_price is None
```

- [ ] **Step 2: Run the watchlist view tests to verify they fail**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_watchlist_view_repository.py" -q`
Expected: FAIL with an import error for `WatchlistViewRepository`

- [ ] **Step 3: Implement a `WatchlistRow` result type and a latest-snapshot subquery**

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlmodel import select
from sqlalchemy import func


@dataclass(slots=True)
class WatchlistRow:
    security_id: int
    code: str
    name: str
    industry: str | None
    last_price: Decimal | None
    change_percent: Decimal | None
    snapshot_time: datetime | None
```

```python
latest_snapshot_subquery = (
    select(
        QuoteSnapshot.security_id,
        func.max(QuoteSnapshot.snapshot_time).label("latest_snapshot_time"),
    )
    .group_by(QuoteSnapshot.security_id)
    .subquery()
)
```

- [ ] **Step 4: Implement `list_rows()` using outer joins so missing quotes still return the security row**

```python
def list_rows(self) -> list[WatchlistRow]:
    statement = (
        select(Security, QuoteSnapshot)
        .join(WatchlistItem, WatchlistItem.security_id == Security.id)
        .outerjoin(latest_snapshot_subquery, latest_snapshot_subquery.c.security_id == Security.id)
        .outerjoin(
            QuoteSnapshot,
            (QuoteSnapshot.security_id == Security.id)
            & (QuoteSnapshot.snapshot_time == latest_snapshot_subquery.c.latest_snapshot_time),
        )
        .order_by(Security.market, Security.code)
    )

    results = self.session.exec(statement).all()
    return [
        WatchlistRow(
            security_id=security.id,
            code=security.code,
            name=security.name,
            industry=security.industry,
            last_price=quote.last_price if quote else None,
            change_percent=quote.change_percent if quote else None,
            snapshot_time=quote.snapshot_time if quote else None,
        )
        for security, quote in results
    ]
```

- [ ] **Step 5: Run the watchlist view tests again**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_watchlist_view_repository.py" -q`
Expected: PASS

## Chunk 3: Bootstrap Data, Module Docs, and Final Verification

### Task 6: Implement normalized bootstrap ingestion for securities and quote snapshots

**Files:**
- Create: `backend/app/db/services/__init__.py`
- Create: `backend/app/db/services/bootstrap_data.py`
- Create: `backend/tests/db/test_bootstrap_data.py`
- Modify: `backend/app/db/repositories/security_repository.py`
- Test: `backend/tests/db/test_bootstrap_data.py`

- [ ] **Step 1: Write the failing bootstrap ingestion test**

```python
from app.db.services.bootstrap_data import bootstrap_market_data


def test_bootstrap_market_data_upserts_securities_and_quotes(session):
    bootstrap_market_data(
        session,
        securities=[
            {"market": "SZ", "code": "000001", "name": "平安银行", "industry": "银行", "status": "active"},
        ],
        quote_snapshots=[
            {
                "market": "SZ",
                "code": "000001",
                "last_price": "12.30",
                "change_amount": "0.15",
                "change_percent": "1.23",
                "snapshot_time": "2026-03-10T15:00:00",
            },
        ],
    )

    rows = WatchlistViewRepository(session).list_rows()
    assert rows == []  # no watchlist entry yet
    assert SecurityRepository(session).search("000001")[0].name == "平安银行"
```

- [ ] **Step 2: Run the bootstrap test to verify it fails**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_bootstrap_data.py" -q`
Expected: FAIL with an import error for `bootstrap_market_data`

- [ ] **Step 3: Implement `bootstrap_market_data()` around normalized input dictionaries**

```python
from datetime import datetime
from decimal import Decimal

from sqlmodel import Session, select


def bootstrap_market_data(session: Session, *, securities: list[dict], quote_snapshots: list[dict]) -> None:
    security_repo = SecurityRepository(session)
    security_repo.upsert_many(securities)

    security_lookup = {
        (row.market, row.code): row
        for row in session.exec(select(Security)).all()
    }

    for item in quote_snapshots:
        security = security_lookup[(item["market"], item["code"])]
        session.add(
            QuoteSnapshot(
                security_id=security.id,
                last_price=Decimal(item["last_price"]),
                change_amount=Decimal(item["change_amount"]),
                change_percent=Decimal(item["change_percent"]),
                snapshot_time=datetime.fromisoformat(item["snapshot_time"]),
            )
        )
    session.commit()
```

- [ ] **Step 4: Run the bootstrap test again**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_bootstrap_data.py" -q`
Expected: PASS

### Task 7: Run the data-layer verification suite and sync project docs for review

**Files:**
- Modify: `docs/modules/data-layer.md`
- Modify: `docs/02-module-registry.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: all `backend/tests/db/*.py`

- [ ] **Step 1: Run the full data-layer test suite**

Run: `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db" -q`
Expected: all tests PASS

- [ ] **Step 2: Record stable implementation decisions**

Add to `memory/decisions.md`:

```md
- 2026-03-10: The first executable code for the watchlist MVP lives in `backend/`.
- 2026-03-10: The local MVP uses SQLite persistence through SQLModel; PostgreSQL remains a later migration target.
- 2026-03-10: Data bootstrap accepts normalized records and does not fetch external market data directly.
```

- [ ] **Step 3: Update the data-layer module document with actual implementation scope and verification commands**

Add or update these points in `docs/modules/data-layer.md`:

```md
## Verification
- `python -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db" -q`
- search ordering verified for exact code, exact name, code prefix, and name contains
- latest quote selection verified by `snapshot_time`
- missing-quote watchlist rows verified to render with null quote fields
```

- [ ] **Step 4: Move the active module into review and update progress memory**

Update:
- `docs/02-module-registry.md`: set `data-layer` to `review`
- `memory/progress.md`: set the next step to backend planning for search, add/remove watchlist item, and watchlist list APIs

- [ ] **Step 5: Run `@superpowers:requesting-code-review` for the completed module**

Expected: review findings are recorded and any required fixes are applied before completion claims

- [ ] **Step 6: Run `@superpowers:verification-before-completion` before moving the module to done**

Expected: evidence-based verification confirms the module is ready for completion

- [ ] **Step 7: If both review skills pass, mark the module done and record the review date**

Update:
- `docs/02-module-registry.md`: set `data-layer` to `done` and fill `Last Review`
- `memory/progress.md`: set the next active planning target to `backend`

## Final Notes
- Keep all code changes scoped to the data-layer module; do not add API routes or UI code while executing this plan.
- If execution reveals that a seed/import script is required outside Python module code, stop and create a separate `scripts` module plan instead of expanding this one silently.
- If git is initialized before execution, create one commit per chunk after the full chunk test suite passes. If git is still not initialized, skip commit steps rather than inventing git history.
