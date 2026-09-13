# Watchlist MVP Runnable Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the completed watchlist MVP runnable end-to-end locally with a seeded SQLite database, a startable backend API, and a frontend that can talk to that backend during development.

**Architecture:** Keep the existing backend and frontend modules intact, and add only the minimal integration glue in the `scripts`/setup layer: backend startup support, seed/bootstrap command(s), and Vite dev proxy wiring. The resulting local workflow should be: seed database → start backend → start frontend → verify the watchlist flow against real local processes.

**Tech Stack:** Python 3.12, FastAPI, SQLModel/SQLite, React, Vite, npm.

---

## File Structure

### Existing files to modify
- Modify: `backend/pyproject.toml` — add runtime server dependency if missing.
- Modify: `backend/app/main.py` — expose a stable ASGI entrypoint if needed.
- Modify: `backend/app/core/settings.py` — optionally support env-configurable DB path or API host settings if needed for local run.
- Modify: `backend/app/db/services/bootstrap_data.py` — only if a thin seed wrapper is needed around existing ingestion logic.
- Modify: `frontend/vite.config.ts` — add local dev proxy for `/api` requests.
- Modify: `docs/modules/scripts.md` — record the integration/setup files, verification, and review evidence if this work activates scripts/integration scope.
- Modify: `docs/02-module-registry.md` — update module state if scripts becomes active for this integration slice.
- Modify: `memory/progress.md` — track current integration work and next step.
- Modify: `memory/decisions.md` — record stable local-run decisions.

### New setup/runtime files
- Create: `backend/app/db/services/seed_demo_data.py` — small service wrapper for a deterministic local demo dataset.
- Create: `backend/scripts/seed_watchlist_demo.py` — CLI script to initialize tables and seed demo securities/quotes.
- Create: `backend/tests/db/test_seed_demo_data.py` — verifies demo seeding creates expected rows.
- Create: `backend/tests/api/test_runtime_smoke.py` — verifies seeded backend app can serve basic API responses through TestClient.
- Create: `scripts/run_backend.sh` — starts backend app locally with the project venv.
- Create: `scripts/run_frontend.sh` — starts Vite frontend locally.
- Create: `scripts/smoke_watchlist.sh` — optional shell smoke check for backend endpoints after seeding.

### Explicitly deferred files
- Do not add Docker, Compose, or deployment manifests in this slice.
- Do not add authentication, production process management, or reverse proxy config.
- Do not add external live market ingestion; use only local seeded demo data.

## Chunk 1: Seeded Backend Runtime

### Task 1: Add backend runtime dependency and demo seed command

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/db/services/seed_demo_data.py`
- Create: `backend/scripts/seed_watchlist_demo.py`
- Create: `backend/tests/db/test_seed_demo_data.py`
- Test: `backend/tests/db/test_seed_demo_data.py`

- [ ] **Step 1: Write the failing seed demo data test**

```python
from app.db.services.seed_demo_data import seed_demo_watchlist_data


def test_seed_demo_watchlist_data_creates_demo_security_and_quote(session):
    seed_demo_watchlist_data(session)

    securities = session.exec(select(Security)).all()
    quotes = session.exec(select(QuoteSnapshot)).all()

    assert len(securities) >= 2
    assert len(quotes) >= 1
```

- [ ] **Step 2: Run the seed test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/db/test_seed_demo_data.py" -q`
Expected: FAIL with missing module or missing seed function

- [ ] **Step 3: Implement a deterministic demo seed service on top of `bootstrap_market_data()`**

```python
def seed_demo_watchlist_data(session: Session) -> None:
    bootstrap_market_data(
        session,
        securities=[
            {"market": "SZ", "code": "000001", "name": "Ping An Bank", "industry": "Banking"},
            {"market": "SH", "code": "600519", "name": "Kweichow Moutai", "industry": "Beverages"},
        ],
        quote_snapshots=[
            {
                "market": "SZ",
                "code": "000001",
                "last_price": "10.5000",
                "change_amount": "0.5000",
                "change_percent": "5.0000",
                "snapshot_time": "2026-03-11T09:30:00+00:00",
            }
        ],
    )
```

- [ ] **Step 4: Implement a CLI seed script that creates tables and seeds the demo dataset**

```python
engine = make_engine(Settings())
create_db_and_tables(engine)
with make_session(engine) as session:
    seed_demo_watchlist_data(session)
```

- [ ] **Step 5: Re-run the seed test**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/db/test_seed_demo_data.py" -q`
Expected: PASS

### Task 2: Verify the backend app can serve seeded watchlist endpoints

**Files:**
- Create: `backend/tests/api/test_runtime_smoke.py`
- Test: `backend/tests/api/test_runtime_smoke.py`

- [ ] **Step 1: Write the failing backend smoke test using the seeded database**

```python
def test_seeded_backend_serves_search_and_watchlist_endpoints(client, session):
    seed_demo_watchlist_data(session)

    search_response = client.get("/api/watchlist/securities/search", params={"query": "000001"})
    list_response = client.get("/api/watchlist/items")

    assert search_response.status_code == 200
    assert list_response.status_code == 200
```

- [ ] **Step 2: Run the smoke test to verify it fails before implementation adjustments**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/api/test_runtime_smoke.py" -q`
Expected: FAIL if the seed helper is not wired into runtime tests yet

- [ ] **Step 3: Implement any minimal runtime glue needed so the seeded backend responds correctly**

```python
# keep changes minimal; likely import/use the new seed service in test only
```

- [ ] **Step 4: Re-run the smoke test**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/api/test_runtime_smoke.py" -q`
Expected: PASS

## Chunk 2: Local Frontend↔Backend Development Wiring

### Task 3: Add Vite proxy support and startup scripts

**Files:**
- Modify: `frontend/vite.config.ts`
- Create: `scripts/run_backend.sh`
- Create: `scripts/run_frontend.sh`
- Create: `scripts/smoke_watchlist.sh`
- Test: manual smoke commands and script execution

- [ ] **Step 1: Add a failing smoke script expectation for the backend search endpoint**

```bash
curl -sf "http://127.0.0.1:8000/api/watchlist/securities/search?query=000001"
```

- [ ] **Step 2: Update `frontend/vite.config.ts` with a dev proxy for `/api`**

```ts
server: {
  proxy: {
    "/api": "http://127.0.0.1:8000",
  },
}
```

- [ ] **Step 3: Add a backend run script that starts uvicorn with the backend venv**

```bash
PYTHONPATH="backend" \
"backend/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- [ ] **Step 4: Add a frontend run script that starts Vite**

```bash
npm run dev --prefix "frontend"
```

- [ ] **Step 5: Add a shell smoke script that checks the backend API after seeding**

```bash
PYTHONPATH="backend" \
"backend/.venv/bin/python" \
"backend/scripts/seed_watchlist_demo.py"
curl -sf "http://127.0.0.1:8000/api/watchlist/securities/search?query=000001"
```

## Chunk 3: Runnable Acceptance Verification and Script-State Sync

### Task 4: Verify runnable local workflow and sync scripts/integration docs

**Files:**
- Modify: `docs/modules/scripts.md`
- Modify: `docs/02-module-registry.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: backend seed/smoke tests + frontend/backend startup commands

- [ ] **Step 1: Run all new integration-oriented automated tests**

Run:
- `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/db/test_seed_demo_data.py" -q`
- `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/api/test_runtime_smoke.py" -q`
- `npm test --prefix "frontend"`

Expected: all pass

- [ ] **Step 2: Run the seed script directly**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" "backend/scripts/seed_watchlist_demo.py"`
Expected: exits successfully and creates/updates local SQLite data

- [ ] **Step 3: Start backend and verify the search endpoint responds**

Run in background: `scripts/run_backend.sh`
Then run: `scripts/smoke_watchlist.sh`
Expected: backend starts and the search smoke check returns JSON successfully

- [ ] **Step 4: Start frontend locally and confirm dev startup succeeds**

Run in background: `scripts/run_frontend.sh`
Expected: Vite starts successfully with `/api` proxy configured

- [ ] **Step 5: Update scripts module doc with actual setup/runtime scope and verification commands**

Add or update these points in `docs/modules/scripts.md`:

```md
## Verification
- backend demo seed command runs successfully
- backend smoke endpoint returns JSON after startup
- frontend dev server starts with `/api` proxy configured
- setup scripts do not alter module boundaries beyond local run support
```

- [ ] **Step 6: Record stable local-run decisions**

Add to `memory/decisions.md`:

```md
- 2026-03-11: Local watchlist MVP runtime uses a seeded SQLite database plus uvicorn and Vite dev servers.
- 2026-03-11: Vite proxies `/api` requests to the local FastAPI backend at `http://127.0.0.1:8000` during development.
```

- [ ] **Step 7: Sync progress for acceptance handoff**

Update `memory/progress.md` so the next step clearly says the project is ready for end-to-end acceptance with local run commands.

## Final Notes
- Keep this slice focused on local-run enablement only; do not introduce deployment infrastructure.
- If the backend needs a missing package for runtime startup (for example uvicorn), add only that minimal dependency.
- Use the existing seeded demo data to prove the stack runs end-to-end before asking for acceptance.
