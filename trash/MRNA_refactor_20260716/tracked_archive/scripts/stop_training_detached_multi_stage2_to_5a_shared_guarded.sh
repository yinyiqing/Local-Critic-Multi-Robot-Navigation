#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.train_multi_stage2_to_5a_shared_guarded_detached.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No detached stage2-to-5A guarded training pid file found."
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -z "$pid" ]]; then
  rm -f "$PID_FILE"
  echo "Removed empty pid file."
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  echo "Stopped detached stage2-to-5A guarded training process group led by PID $pid"
else
  echo "PID $pid is not running."
fi

rm -f "$PID_FILE"
