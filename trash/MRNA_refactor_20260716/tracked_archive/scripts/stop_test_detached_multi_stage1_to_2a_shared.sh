#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.test_multi_stage1_to_2a_shared_detached.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No detached stage1-to-2A shared-policy test pid file found."
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
  kill -- "-$pid" 2>/dev/null || kill "$pid" || true
  echo "Stopped detached stage1-to-2A shared-policy test process group led by PID $pid"
else
  echo "PID $pid is not running."
fi

rm -f "$PID_FILE"
