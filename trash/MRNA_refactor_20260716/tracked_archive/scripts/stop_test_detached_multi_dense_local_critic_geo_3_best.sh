#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.test_multi_dense_local_critic_geo_3_best_detached.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No detached dense 3-agent geometry-only local-critic best-model test pid file found."
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
  kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  echo "Stopped detached dense 3-agent geometry-only local-critic best-model test process group led by PID $pid"
else
  echo "No running dense 3-agent geometry-only local-critic best-model test process found for PID $pid"
fi

rm -f "$PID_FILE"
