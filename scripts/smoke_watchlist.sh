#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
SMOKE_DB_PATH="$ROOT_DIR/investment_board_smoke.db"
DATABASE_URL="sqlite:///$SMOKE_DB_PATH"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ ! -x "$VENV_PYTHON" ]]; then
  printf 'Backend virtualenv python not found at %s\n' "$VENV_PYTHON" >&2
  exit 1
fi

if ! "$VENV_PYTHON" -c 'import uvicorn' >/dev/null 2>&1; then
  printf 'uvicorn is not installed in the backend virtualenv at %s\n' "$VENV_PYTHON" >&2
  exit 1
fi

rm -f "$SMOKE_DB_PATH"

printf 'Seeding demo data into %s\n' "$DATABASE_URL"
(
  cd "$BACKEND_DIR"
  DATABASE_URL="$DATABASE_URL" "$VENV_PYTHON" -m app.db.services.seed_demo_data_cli
)

printf 'Starting backend for smoke test\n'
(
  cd "$BACKEND_DIR"
  DATABASE_URL="$DATABASE_URL" "$VENV_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
) >"$ROOT_DIR/.smoke_backend.log" 2>&1 &
SERVER_PID=$!

for _ in {1..20}; do
  if curl --silent --show-error --fail "http://127.0.0.1:8000/api/watchlist/items" >/dev/null; then
    break
  fi
  sleep 1
done

printf 'Checking seeded watchlist endpoint\n'
watchlist_response="$(curl --silent --show-error --fail "http://127.0.0.1:8000/api/watchlist/items")"
printf '%s\n' "$watchlist_response"
printf '%s' "$watchlist_response" | python3 -c 'import json, sys; items = json.load(sys.stdin); assert len(items) == 2, items; assert items[0]["code"] == "600519", items; assert items[1]["code"] == "000001", items'

printf 'Checking seeded search endpoint\n'
search_response="$(curl --silent --show-error --fail "http://127.0.0.1:8000/api/watchlist/securities/search?query=Ping")"
printf '%s\n' "$search_response"
printf '%s' "$search_response" | python3 -c 'import json, sys; results = json.load(sys.stdin); assert results, results; assert results[0]["code"] == "000001", results; assert any(item["name"] == "Ping An Bank" for item in results), results'

printf 'Smoke test passed\n'
