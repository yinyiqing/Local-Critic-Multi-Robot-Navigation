#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.train_spatiotemporal_attention_5d_detached.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No attention training PID file found."
  exit 0
fi

pid="$(<"$PID_FILE")"
if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
  kill -INT -- -"$pid"
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      break
    fi
    sleep 0.5
  done
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM -- -"$pid"
  fi
  echo "Stopped attention training process group led by PID $pid after checkpoint request"
fi
rm -f "$PID_FILE"
