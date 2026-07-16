#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.train_multi_local_critic_geo_3_detached.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No detached 3-agent geometry-only local-critic training pid file found."
  exit 0
fi

pid="$(cat "$PID_FILE")"
if kill -0 "$pid" 2>/dev/null; then
  pkill -TERM -P "$pid" 2>/dev/null || true
  kill -TERM "$pid" 2>/dev/null || true
  echo "Stopped detached 3-agent geometry-only local-critic training process group led by PID $pid"
else
  echo "Detached 3-agent geometry-only local-critic training process $pid is not running."
fi

rm -f "$PID_FILE"
