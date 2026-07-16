#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$PROJECT_ROOT/.test_multi_stage1_to_2a_shared_detached.pid"
LAUNCHFILE="multi_robot_scenario_multi_2.launch"
MODEL_NAME="${DRL_MULTI_TEST_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage2_2a_shared_from_stage1g_best}"
ROS_PORT="${DRL_MULTI_TEST_ROS_PORT:-11374}"
GAZEBO_PORT="${DRL_MULTI_TEST_GAZEBO_PORT:-11474}"
TARGET_EPISODES="${DRL_MULTI_TEST_TARGET_EPISODES:-300}"
SAFE_MODEL="${MODEL_NAME//[^A-Za-z0-9_]/_}"

mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/test_multi_stage1_to_2a_shared_${SAFE_MODEL}_detached_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached stage1-to-2A shared-policy test process is already running with PID $old_pid"
    exit 1
  fi
fi

if [[ ! -f "$TD3_DIR/pytorch_models/${MODEL_NAME}_actor.pth" ]]; then
  echo "Actor model is missing: $TD3_DIR/pytorch_models/${MODEL_NAME}_actor.pth"
  exit 1
fi

setsid bash -lc "
  source /opt/ros/noetic/setup.bash
  source '$PROJECT_ROOT/env.python.sh'
  export ROS_HOSTNAME=localhost
  export ROS_MASTER_URI=http://localhost:${ROS_PORT}
  export ROS_PORT_SIM=${ROS_PORT}
  export GAZEBO_MASTER_URI=http://localhost:${GAZEBO_PORT}
  export GAZEBO_RESOURCE_PATH='$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch'
  export DRL_MULTI_NUM_AGENTS=2
  export DRL_MULTI_TEST_LAUNCHFILE='$LAUNCHFILE'
  export DRL_MULTI_TEST_FILE_NAME='$MODEL_NAME'
  export DRL_MULTI_TEST_TARGET_EPISODES='$TARGET_EPISODES'
  export DRL_MULTI_TEST_STATE_PATH='./checkpoints/${SAFE_MODEL}_standard_2a_test_state.pt'
  export DRL_MULTI_TEST_STATS_PATH='./results/${SAFE_MODEL}_standard_2a_test.npy'
  export DRL_MULTI_SCENARIO=standard
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u test_velodyne_td3_multi.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached stage1-to-2A shared-policy test started."
echo "PID: $(cat "$PID_FILE")"
echo "Agents: 2"
echo "Model: $MODEL_NAME"
echo "Launch: $LAUNCHFILE"
echo "Scenario: standard"
echo "Target episodes: $TARGET_EPISODES"
echo "Log: $log_file"
