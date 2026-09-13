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
- `scripts/smoke_watchlist.py`
- `scripts/run_all.sh`
- `scripts/tests/test_launchers.py`
- `scripts/tests/test_smoke_watchlist.py`

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
review

## Recommended Skills
- `superpowers:brainstorming` for script scope changes
- `superpowers:writing-plans` for implementation breakdown
- `superpowers:systematic-debugging` for script failures
- `superpowers:requesting-code-review` when module work is complete
- `superpowers:verification-before-completion` before setting status to `done`

## Verification
- `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/db/test_seed_demo_data.py" -q`
- `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/api/test_runtime_smoke.py" -q`
- `npm test --prefix "frontend"`
- `scripts/smoke_watchlist.sh`
- `curl -s http://127.0.0.1:8000/api/watchlist/items`
- `curl -s "http://127.0.0.1:8000/api/watchlist/securities/search?query=Ping"`
- `python3 - <<'PY' ... urlopen('http://127.0.0.1:5173') ... PY`

## Review Evidence
- Review date: 2026-09-13.
- Script regressions: 15 passed; independent specification and quality reviews passed.
- Standalone smoke verifies the two exact seeded watchlist identities and local search using an isolated temporary database, held loopback socket and owned child process.
- Parallel runs, foreign occupied ports, invalid timeouts, startup failures, outer harness timeouts, SIGINT/SIGTERM and cleanup are covered. Default startup deadline is 120 seconds and may be overridden with a finite positive `SMOKE_STARTUP_TIMEOUT`.
- Actual combined launcher stop/restart verified termination of all owned processes and release/reuse of ports 8000/5173.
- Migration metadata repair verified the virtualenv activation path, external-directory backend import and disposable-database seed entrypoint.
- Consolidated verification: `docs/verification/release-readiness.md`.

## Repository Packaging Scope
Included: current verified sources, project-introduction README, two actual demo runtime screenshots, portable example settings, contribution guidance, CI and version-control hygiene. Dependencies, build outputs, personal data, credentials and raw local verification artifacts remain outside version control.

Excluded: changing repository visibility, rewriting Git history, assigning a new license, or adding new product features. Preserve current external-AI acceptance limitations.

## Packaging Verification
- Review README claims and links against current source and screenshots.
- Exercise clean-source installation and existing backend/frontend/script checks.
- Inspect the staged tree for runtime databases, dependencies and credentials.
- Use a normal history-preserving push to the existing default branch and verify remote contents.
