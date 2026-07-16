#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.train_multi_local_critic_geo_reward_only_5_detached.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No detached 5-agent reward-only geometry local-critic training pid file found."
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
  kill -- "-$pid" 2>/dev/null || kill "$pid" || true
  echo "Stopped detached 5-agent reward-only geometry local-critic training process group led by PID $pid"
else
  echo "PID $pid is not running."
fi

rm -f "$PID_FILE"
