# Run-All Script Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single root-level launcher script that can optionally seed demo data and then start the backend and frontend together for local development.

**Architecture:** Build one thin orchestration shell script in `scripts/run_all.sh` that reuses the existing `run_backend.sh` and `run_frontend.sh` scripts instead of re-implementing startup logic. Keep process management simple: optional seed step, start two child processes, print URLs, trap shutdown signals, and clean up both children on exit.

**Tech Stack:** Bash, existing backend seed command, existing backend/frontend run scripts.

---

## File Structure

### Existing files to modify
- Modify: `scripts/run_backend.sh` only if a tiny compatibility adjustment is required for orchestration.
- Modify: `scripts/run_frontend.sh` only if a tiny compatibility adjustment is required for orchestration.
- Modify: `docs/modules/scripts.md` — record the new launcher and verification evidence.
- Modify: `docs/02-module-registry.md` only if script module status needs a review-date refresh.
- Modify: `memory/progress.md` — sync current progress and next step.
- Modify: `memory/decisions.md` — record the launcher behavior if it becomes a stable workflow decision.

### New files
- Create: `scripts/run_all.sh` — one-command local launcher with optional seeding and coordinated shutdown.
- Create: `scripts/tests/test_run_all_smoke.sh` — lightweight shell smoke test for launcher argument handling and startup contract if practical.

### Explicitly deferred files
- Do not add tmux, pm2, Docker, Compose, or production process management.
- Do not add dependency installation logic.
- Do not add logging/rotation infrastructure.

## Chunk 1: Launcher Script

### Task 1: Create `run_all.sh` with optional seed and coordinated process lifecycle

**Files:**
- Create: `scripts/run_all.sh`
- Test: manual launcher invocation

- [ ] **Step 1: Write the failing launcher smoke expectation**

Run: `./scripts/run_all.sh --help`
Expected: FAIL because the launcher does not exist yet

- [ ] **Step 2: Create the launcher script with argument parsing**

```bash
#!/usr/bin/env bash
set -euo pipefail

SEED_FIRST=false
if [[ "${1:-}" == "--seed" ]]; then
  SEED_FIRST=true
fi
```

- [ ] **Step 3: Add preflight checks and optional seed step**

```bash
if [[ "$SEED_FIRST" == true ]]; then
  (cd "$ROOT_DIR/backend" && ./.venv/bin/seed-watchlist-demo)
fi
```

- [ ] **Step 4: Start backend and frontend as child processes and trap shutdown**

```bash
"$ROOT_DIR/scripts/run_backend.sh" &
BACKEND_PID=$!
"$ROOT_DIR/scripts/run_frontend.sh" &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
  wait "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait
```

- [ ] **Step 5: Print clear startup output**

```bash
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:5173"
echo "Press Ctrl+C to stop both services"
```

- [ ] **Step 6: Verify the launcher starts and can be interrupted cleanly**

Run: `./scripts/run_all.sh --seed`
Expected: both backend and frontend start, URLs print, Ctrl+C stops both processes

## Chunk 2: Verification and Doc Sync

### Task 2: Record launcher verification and usage

**Files:**
- Modify: `docs/modules/scripts.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`

- [ ] **Step 1: Re-run the existing smoke script and launcher manually**

Run:
- `./scripts/smoke_watchlist.sh`
- `./scripts/run_all.sh --seed`

Expected: smoke passes and launcher starts both services successfully

- [ ] **Step 2: Update scripts module doc with launcher usage**

Add:

```md
- `scripts/run_all.sh` starts frontend and backend together
- `scripts/run_all.sh --seed` seeds demo data before startup
```

- [ ] **Step 3: Update progress and decisions**

Record that the project now supports one-command local startup for acceptance and development.

## Final Notes
- Keep the launcher lightweight and development-only.
- Reuse the existing scripts instead of duplicating their logic.
- Prefer clear failure messages over hidden retries or background daemon behavior.
