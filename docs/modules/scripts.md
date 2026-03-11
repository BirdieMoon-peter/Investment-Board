# Scripts Module

## Goal
Define and implement developer or operational scripts that support the project workflow, automation, and maintenance.

## Scope
Included:
- local developer scripts
- project automation helpers
- maintenance or setup scripts
- script-specific verification items

Excluded:
- core frontend features
- core backend business logic
- primary data model design unless a script directly manages it

## Interfaces
- command-line script entry points
- script inputs, outputs, and expected side effects
- script dependencies on application modules

## Tasks
- [x] Define which scripts are needed for the current milestone
- [x] Document inputs, outputs, and usage expectations
- [x] Identify dependencies on frontend, backend, or data-layer modules
- [x] Define verification steps for successful and failing executions

## Implemented Files
- `backend/app/db/services/seed_demo_data.py`
- `backend/app/db/services/seed_demo_data_cli.py`
- `backend/scripts/seed_watchlist_demo.py`
- `backend/tests/db/test_seed_demo_data.py`
- `backend/tests/api/test_runtime_smoke.py`
- `scripts/run_backend.sh`
- `scripts/run_frontend.sh`
- `scripts/smoke_watchlist.sh`

## Consumers
- Local developers can use `seed-watchlist-demo` or `backend/scripts/seed_watchlist_demo.py` to initialize demo data.
- Local developers can use `scripts/run_backend.sh` to start the FastAPI backend against the project database.
- Local developers can use `scripts/run_frontend.sh` to start the Vite frontend with `/api` proxy support.
- Local developers can use `scripts/smoke_watchlist.sh` to seed a smoke database, start the backend, and verify key watchlist endpoints.

## Current Milestone
Optional setup scripts for watchlist MVP

## Milestone Scope
Only include scripts in this milestone if required for setup:
- security master data seed/import
- minimal quote snapshot seed/sync

Deferred in this milestone:
- recurring developer automation unrelated to watchlist setup
- operational scripts outside MVP bootstrap

## Current Status
done

## Recommended Skills
- `superpowers:brainstorming` for script scope changes
- `superpowers:writing-plans` for implementation breakdown
- `superpowers:systematic-debugging` for script failures
- `superpowers:requesting-code-review` when module work is complete
- `superpowers:verification-before-completion` before setting status to `done`

## Verification
- `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_seed_demo_data.py" -q`
- `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_runtime_smoke.py" -q`
- `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend"`
- `scripts/smoke_watchlist.sh`
- `curl -s http://127.0.0.1:8000/api/watchlist/items`
- `curl -s "http://127.0.0.1:8000/api/watchlist/securities/search?query=Ping"`
- `python3 - <<'PY' ... urlopen('http://127.0.0.1:5173') ... PY`

## Review Evidence
- Date: 2026-03-11
- Verification commands:
  - `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db/test_seed_demo_data.py" -q`
  - `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_runtime_smoke.py" -q`
  - `npm test --prefix "/Users/peter/Desktop/Investment Board/frontend"`
  - `scripts/smoke_watchlist.sh`
  - `curl -s http://127.0.0.1:8000/api/watchlist/items`
  - `curl -s "http://127.0.0.1:8000/api/watchlist/securities/search?query=Ping"`
  - `python3 - <<'PY' ... urlopen('http://127.0.0.1:5173') ... PY`
- Result summary:
  - backend seed tests pass
  - backend runtime smoke test passes
  - frontend test suite passes
  - backend smoke script passes against a seeded local database
  - backend and frontend dev servers both respond locally
- Remaining follow-up items:
  - A browser-level manual acceptance pass is still useful when the user returns.

## Open Questions
- Which recurring project actions should be automated first?
- Are these scripts for development only, or also for operations?
