#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
DEFAULT_DATABASE_URL="sqlite:///$ROOT_DIR/investment_board.db"

if [[ ! -x "$VENV_PYTHON" ]]; then
  printf 'Backend virtualenv python not found at %s\n' "$VENV_PYTHON" >&2
  exit 1
fi

if ! "$VENV_PYTHON" -c 'import uvicorn' >/dev/null 2>&1; then
  printf 'uvicorn is not installed in the backend virtualenv at %s\n' "$VENV_PYTHON" >&2
  exit 1
fi

cd "$BACKEND_DIR"
export DATABASE_URL="${DATABASE_URL:-$DEFAULT_DATABASE_URL}"
exec "$VENV_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
