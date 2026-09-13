#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
VITE_ENTRY="$FRONTEND_DIR/node_modules/vite/bin/vite.js"

if ! command -v node >/dev/null 2>&1; then
  printf 'Node.js is required to start the frontend.\n' >&2
  exit 1
fi

if [[ ! -f "$VITE_ENTRY" ]]; then
  printf 'Vite is not installed at %s. Run npm install in the frontend directory.\n' "$VITE_ENTRY" >&2
  exit 1
fi

cd "$FRONTEND_DIR"
exec node "$VITE_ENTRY" --host 127.0.0.1 --port 5173 --strictPort
