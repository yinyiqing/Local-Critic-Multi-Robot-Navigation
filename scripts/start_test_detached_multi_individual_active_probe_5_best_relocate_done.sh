#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$PROJECT_ROOT/.test_multi_individual_active_probe_5_best_relocate_done_detached.pid"
NUM_AGENTS=5
LAUNCHFILE="multi_robot_scenario_individual_active_probe_${NUM_AGENTS}.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCHFILE"
MODEL_NAME="TD3_velodyne_multi_v4_individual_active_probe_5_best"
RESULT_NAME="${MODEL_NAME}_relocate_done"
ROS_PORT="${DRL_MULTI_TEST_ROS_PORT:-11368}"
GAZEBO_PORT="${DRL_MULTI_TEST_GAZEBO_PORT:-11408}"
TARGET_EPISODES="${DRL_MULTI_TEST_TARGET_EPISODES:-300}"

mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/test_multi_individual_active_probe_5_best_relocate_done_detached_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached 5-agent individual-active-probe relocate-done test process is already running with PID $old_pid"
    exit 1
  fi
fi

if [[ ! -f "$TD3_DIR/pytorch_models/${MODEL_NAME}_actor.pth" ]]; then
  echo "Best actor model is missing: $TD3_DIR/pytorch_models/${MODEL_NAME}_actor.pth"
  echo "Run 5-agent individual-active-probe training until at least one eval updates the best checkpoint."
  exit 1
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
  export DRL_MULTI_NUM_AGENTS='$NUM_AGENTS'
  export DRL_MULTI_TEST_LAUNCHFILE='$LAUNCHFILE'
  export DRL_MULTI_TEST_FILE_NAME='$MODEL_NAME'
  export DRL_MULTI_TEST_STATE_PATH='./checkpoints/${RESULT_NAME}_test_state.pt'
  export DRL_MULTI_TEST_STATS_PATH='./results/${RESULT_NAME}_test.npy'
  export DRL_MULTI_TEST_TARGET_EPISODES='$TARGET_EPISODES'
  export DRL_MULTI_RELOCATE_SUCCESSFUL_DONE_AGENTS=1
  export DRL_MULTI_DONE_AGENT_HOLDING_X=20.0
  export DRL_MULTI_DONE_AGENT_HOLDING_Y=20.0
  export DRL_MULTI_DONE_AGENT_HOLDING_SPACING=2.0
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u test_velodyne_td3_multi.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached 5-agent individual-active-probe relocate-done best-model test started."
echo "PID: $(cat "$PID_FILE")"
echo "Model: $MODEL_NAME"
echo "Results: $TD3_DIR/results/${RESULT_NAME}_test.npy"
echo "Launch: $LAUNCH_PATH"
echo "Target episodes: $TARGET_EPISODES"
echo "Done-agent relocation: successful agents moved to holding area"
echo "Log: $log_file"
