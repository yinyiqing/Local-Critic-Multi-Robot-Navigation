#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NUM_AGENTS="${1:-3}"
PID_FILE="$PROJECT_ROOT/.capacity_check_multi_${NUM_AGENTS}.pid"
ROS_PORT="${DRL_CAPACITY_ROS_PORT:-11341}"
GAZEBO_PORT="${DRL_CAPACITY_GAZEBO_PORT:-11381}"
LAUNCH_BASENAME="multi_robot_scenario_capacity_${NUM_AGENTS}.launch"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No detached ${NUM_AGENTS}-agent capacity check pid file found."
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
  kill -- "-$pid" 2>/dev/null || kill "$pid" || true
  echo "Stopped detached ${NUM_AGENTS}-agent capacity check process group led by PID $pid"
else
  echo "PID $pid is not running."
fi

rm -f "$PID_FILE"

pkill -f "roslaunch -p ${ROS_PORT} .*${LAUNCH_BASENAME}" 2>/dev/null || true
pkill -f "roscore -p ${ROS_PORT}" 2>/dev/null || true
pkill -f "gzserver.*${GAZEBO_PORT}" 2>/dev/null || true
pkill -f "gzclient.*${GAZEBO_PORT}" 2>/dev/null || true
