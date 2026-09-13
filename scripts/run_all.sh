#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
BACKEND_SCRIPT="$ROOT_DIR/scripts/run_backend.sh"
FRONTEND_SCRIPT="$ROOT_DIR/scripts/run_frontend.sh"
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
DEFAULT_DATABASE_URL="sqlite:///$ROOT_DIR/investment_board.db"
BACKEND_PID=""
FRONTEND_PID=""
SEED_FIRST=false

usage() {
  printf 'Usage: %s [--seed] [--help]\n' "$(basename "$0")"
  printf '\n'
  printf 'Start the local backend and frontend development servers together.\n'
  printf '\n'
  printf 'Options:\n'
  printf '  --seed    Seed demo data before starting both services\n'
  printf '  --help    Show this help message\n'
}

cleanup() {
  local exit_code=$?

  trap - EXIT INT TERM

  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  if [[ -n "$BACKEND_PID" ]]; then
    wait "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "$FRONTEND_PID" ]]; then
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi

  return "$exit_code"
}

seed_demo_data() {
  if [[ ! -x "$VENV_PYTHON" ]]; then
    printf 'Backend virtualenv python not found at %s\n' "$VENV_PYTHON" >&2
    exit 1
  fi

  printf 'Seeding demo data into %s\n' "${DATABASE_URL:-$DEFAULT_DATABASE_URL}"
  (
    cd "$BACKEND_DIR"
    DATABASE_URL="${DATABASE_URL:-$DEFAULT_DATABASE_URL}" "$VENV_PYTHON" -m app.db.services.seed_demo_data_cli
  )
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed)
      SEED_FIRST=true
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ! -x "$BACKEND_SCRIPT" ]]; then
  printf 'Backend launcher not found or not executable at %s\n' "$BACKEND_SCRIPT" >&2
  exit 1
fi

if [[ ! -x "$FRONTEND_SCRIPT" ]]; then
  printf 'Frontend launcher not found or not executable at %s\n' "$FRONTEND_SCRIPT" >&2
  exit 1
fi

if [[ "$SEED_FIRST" == true ]]; then
  seed_demo_data
fi

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"$BACKEND_SCRIPT" &
BACKEND_PID=$!

"$FRONTEND_SCRIPT" &
FRONTEND_PID=$!

printf 'Backend: http://127.0.0.1:8000\n'
printf 'Frontend: http://127.0.0.1:5173\n'
printf 'Press Ctrl+C to stop both services.\n'

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    printf 'Backend process exited. Stopping launcher.\n' >&2
    exit 1
  fi

  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    printf 'Frontend process exited. Stopping launcher.\n' >&2
    exit 1
  fi

  sleep 1
done
