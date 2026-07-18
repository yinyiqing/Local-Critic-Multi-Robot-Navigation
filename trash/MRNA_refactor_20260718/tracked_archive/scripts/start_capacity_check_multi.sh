#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
NUM_AGENTS="${1:-3}"
EPISODES="${DRL_CAPACITY_EPISODES:-5}"
STEPS="${DRL_CAPACITY_STEPS:-80}"
ROS_PORT="${DRL_CAPACITY_ROS_PORT:-11341}"
GAZEBO_PORT="${DRL_CAPACITY_GAZEBO_PORT:-11381}"
PID_FILE="$PROJECT_ROOT/.capacity_check_multi_${NUM_AGENTS}.pid"
LAUNCH_BASENAME="multi_robot_scenario_capacity_${NUM_AGENTS}.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCH_BASENAME"

mkdir -p "$LOG_DIR"

case "$NUM_AGENTS" in
  2|3|5|10) ;;
  *)
    echo "NUM_AGENTS must be one of: 2, 3, 5, 10"
    echo "Usage: bash scripts/start_capacity_check_multi.sh [2|3|5|10]"
    exit 1
    ;;
esac

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/capacity_multi_${NUM_AGENTS}_detached_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached ${NUM_AGENTS}-agent capacity check is already running with PID $old_pid"
    exit 1
  fi
fi

python3 "$PROJECT_ROOT/scripts/generate_multi_robot_launch.py" \
  --num-agents "$NUM_AGENTS" \
  --output "$LAUNCH_PATH"

setsid bash -lc "
  source /opt/ros/noetic/setup.bash
  source '$PROJECT_ROOT/env.python.sh'
  export ROS_HOSTNAME=localhost
  export ROS_MASTER_URI=http://localhost:${ROS_PORT}
  export ROS_PORT_SIM=${ROS_PORT}
  export GAZEBO_MASTER_URI=http://localhost:${GAZEBO_PORT}
  export GAZEBO_RESOURCE_PATH='$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch'
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u check_multi_agent_capacity.py \
    --num-agents '$NUM_AGENTS' \
    --launchfile '$LAUNCH_BASENAME' \
    --episodes '$EPISODES' \
    --steps '$STEPS' \
    --weak-coupling-layout
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached ${NUM_AGENTS}-agent capacity check started."
echo "PID: $(cat "$PID_FILE")"
echo "Launch: $LAUNCH_PATH"
echo "Episodes: $EPISODES"
echo "Steps per episode: $STEPS"
echo "Log: $log_file"
