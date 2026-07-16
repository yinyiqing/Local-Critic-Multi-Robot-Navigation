#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${1:-stage1_single}"
PID_FILE="$PROJECT_ROOT/.train_multi_curriculum_${STAGE}_detached.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No detached curriculum training PID file found for stage: $STAGE"
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
  echo "No running detached curriculum training process found for stage: $STAGE"
  rm -f "$PID_FILE"
  exit 0
fi

pgid="$(ps -o pgid= -p "$pid" | tr -d ' ')"
if [[ -n "$pgid" ]]; then
  kill -- "-$pgid" 2>/dev/null || true
  sleep 2
  kill -9 -- "-$pgid" 2>/dev/null || true
else
  kill "$pid" 2>/dev/null || true
fi
rm -f "$PID_FILE"
echo "Stopped detached curriculum training process group led by PID $pid"
