#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VARIANT="${1:-weighted09_active}"
PID_FILE="$PROJECT_ROOT/.train_multi_${VARIANT}_5_detached.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No detached 5-agent $VARIANT training pid file found."
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -n "$pid" ]]; then
  kill -- "-$pid" 2>/dev/null || true
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
  fi
  echo "Stopped detached 5-agent $VARIANT training process group led by PID $pid"
else
  echo "PID file did not contain a valid PID."
fi

rm -f "$PID_FILE"
