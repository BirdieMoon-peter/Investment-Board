#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  printf 'Backend virtualenv python not found at %s\n' "$VENV_PYTHON" >&2
  exit 1
fi

exec "$VENV_PYTHON" "$ROOT_DIR/scripts/smoke_watchlist.py"
