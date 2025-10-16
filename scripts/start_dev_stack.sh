#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".env" ]; then
  echo "[start_dev_stack] .env file not found in repository root." >&2
  exit 1
fi

# Load environment variables (allow comments)
set -a
source .env
set +a

if [ -z "${DATABASE_URL:-}" ]; then
  echo "[start_dev_stack] DATABASE_URL is not set. Update .env before running this script." >&2
  exit 1
fi

check_command() {
  local cmd="$1" hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[start_dev_stack] '$cmd' is required. ${hint}" >&2
    exit 1
  fi
}

check_command redis-cli "Install via Homebrew: brew install redis"
check_command psql "Install via Homebrew: brew install postgresql@15"
check_command npm "Install Node.js (https://nodejs.org/)"
check_command "$ROOT_DIR/venv/bin/python" "Create the venv with: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"

LOG_DIR="$ROOT_DIR/logs/dev"
mkdir -p "$LOG_DIR"

echo "[start_dev_stack] Verifying Redis connectivity..."
if ! redis-cli ping >/dev/null 2>&1; then
  echo "[start_dev_stack] Redis is not reachable at localhost:6379. Start Redis (e.g., 'redis-server --daemonize yes' or 'brew services start redis')." >&2
  exit 1
fi

echo "[start_dev_stack] Verifying PostgreSQL connectivity..."
"$ROOT_DIR/venv/bin/python" - <<'PYTHON'
import os, sys
from sqlalchemy import create_engine, text
try:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as exc:
    print(f"[start_dev_stack] Unable to connect to PostgreSQL: {exc}", file=sys.stderr)
    sys.exit(1)
PYTHON

echo "[start_dev_stack] Ensuring frontend dependencies..."
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  (cd "$ROOT_DIR/frontend" && npm install)
fi

BACKEND_CMD=("$ROOT_DIR/venv/bin/uvicorn" "main:app" "--host" "127.0.0.1" "--port" "5001" "--reload")
CELERY_WORKER_CMD=("$ROOT_DIR/venv/bin/celery" "-A" "celery_app" "worker" "--loglevel=info" "--pool=solo")
CELERY_BEAT_CMD=("$ROOT_DIR/venv/bin/celery" "-A" "celery_app" "beat" "--loglevel=info")
FRONTEND_CMD=("npm" "run" "dev" "--" "--host" "127.0.0.1" "--port" "3000")

PIDS=()

start_process() {
  local label="$1"
  shift
  local logfile="$LOG_DIR/${label}.log"
  echo "[start_dev_stack] Starting $label (log: $logfile)"
  "$@" >"$logfile" 2>&1 &
  PIDS+=($!)
}

start_process "backend" "${BACKEND_CMD[@]}"
start_process "celery-worker" "${CELERY_WORKER_CMD[@]}"
start_process "celery-beat" "${CELERY_BEAT_CMD[@]}"
start_process "frontend" bash -lc "cd '$ROOT_DIR/frontend' && ${FRONTEND_CMD[*]}"

cleanup() {
  echo
  echo "[start_dev_stack] Shutting down..."
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
      wait "$pid" >/dev/null 2>&1 || true
    fi
  done
  echo "[start_dev_stack] All processes stopped."
}

trap cleanup EXIT
trap 'exit 0' INT

echo "[start_dev_stack] Services up:"
echo "  Backend API:     http://127.0.0.1:5001/api/v1/health"
echo "  Frontend (Vite): http://127.0.0.1:3000/"
echo "  Logs directory:  $LOG_DIR"
echo "Press Ctrl+C to stop everything."

wait
