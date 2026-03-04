#!/bin/bash

# uvicorn 실행 스크립트
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# 가상환경 활성화 (있을 경우)
if [ -f "$APP_DIR/venv/bin/activate" ]; then
    source "$APP_DIR/venv/bin/activate"
fi

echo "Starting uvicorn: http://$HOST:$PORT (workers=$WORKERS)"

uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL"
