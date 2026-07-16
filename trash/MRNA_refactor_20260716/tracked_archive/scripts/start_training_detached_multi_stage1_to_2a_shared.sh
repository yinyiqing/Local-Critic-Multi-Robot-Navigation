#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$PROJECT_ROOT/.train_multi_stage1_to_2a_shared_detached.pid"
LAUNCHFILE="multi_robot_scenario_multi_2.launch"
MODEL_NAME="TD3_velodyne_multi_v4_curriculum_stage2_2a_shared_from_stage1g"
LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best}"
ROS_PORT="${DRL_MULTI_ROS_PORT:-11373}"
GAZEBO_PORT="${DRL_MULTI_GAZEBO_PORT:-11473}"

mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/train_multi_stage1_to_2a_shared_detached_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached stage1-to-2A shared-policy training process is already running with PID $old_pid"
    exit 1
  fi
fi

existing_pid="$(
  (
    pgrep -af "^python3(\\.8)? .*train_velodyne_td3_multi\\.py$" \
      | awk 'NR==1 {print $1}'
  ) || true
)"
if [[ -n "$existing_pid" ]]; then
  echo "A multi-agent training process is already running with PID $existing_pid"
  echo "Please stop the current multi-agent training before starting this run."
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
  export DRL_MULTI_TRAIN_LAUNCHFILE='$LAUNCHFILE'
  export DRL_MULTI_SCENARIO=standard
  export DRL_MULTI_USE_DYNAMIC_REWARD=0
  export DRL_MULTI_USE_DISTANCE_WEIGHTED_REWARD=0
  export DRL_MULTI_USE_LOCAL_CRITIC=0
  export DRL_MULTI_USE_LOCAL_NAVIGATION_REWARD=0
  export DRL_MULTI_USE_WALL_CLEARANCE_REWARD=0
  export DRL_MULTI_BEST_METRIC=success
  export DRL_MULTI_EVAL_EPISODES='${DRL_MULTI_EVAL_EPISODES:-40}'
  export DRL_MULTI_MAX_EPOCHS='${DRL_MULTI_MAX_EPOCHS:-12}'
  export DRL_MULTI_EXPL_NOISE='${DRL_MULTI_EXPL_NOISE:-0.10}'
  export DRL_MULTI_EXPL_MIN='${DRL_MULTI_EXPL_MIN:-0.03}'
  export DRL_MULTI_ACTOR_LR='${DRL_MULTI_ACTOR_LR:-0.00008}'
  export DRL_MULTI_CRITIC_LR='${DRL_MULTI_CRITIC_LR:-0.00008}'
  export DRL_MULTI_TRAINING_VERSION='stage1-to-2a-shared-policy-reset-v1'
  export DRL_MULTI_TRAIN_FILE_NAME='$MODEL_NAME'
  export DRL_MULTI_LOAD_MODEL=1
  export DRL_MULTI_LOAD_MODEL_NAME='$LOAD_MODEL_NAME'
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u train_velodyne_td3_multi.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached stage1-to-2A shared-policy training started."
echo "PID: $(cat "$PID_FILE")"
echo "Agents: 2"
echo "Model: $MODEL_NAME"
echo "Warm start: $LOAD_MODEL_NAME"
echo "Launch: $LAUNCHFILE"
echo "Dynamic reward: 0"
echo "Distance-weighted reward: 0"
echo "Local critic: 0"
echo "Max epochs: ${DRL_MULTI_MAX_EPOCHS:-12}"
echo "Eval episodes: ${DRL_MULTI_EVAL_EPISODES:-40}"
echo "Log: $log_file"
