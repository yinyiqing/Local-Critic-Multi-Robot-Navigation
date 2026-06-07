#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$PROJECT_ROOT/.train_multi_stage2_to_3a_shared_guarded_detached.pid"
NUM_AGENTS=3
LAUNCHFILE="multi_robot_scenario_stage2_to_3a_shared_${NUM_AGENTS}.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCHFILE"
MODEL_NAME="TD3_velodyne_multi_v4_curriculum_stage2_to_3a_shared_from_2d_gentle_guarded"
LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best}"
ROS_PORT="${DRL_MULTI_ROS_PORT:-11376}"
GAZEBO_PORT="${DRL_MULTI_GAZEBO_PORT:-11476}"

mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/train_multi_stage2_to_3a_shared_guarded_detached_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached guarded stage2-to-3A shared-policy training process is already running with PID $old_pid"
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
  export DRL_MULTI_TRAIN_LAUNCHFILE='$LAUNCHFILE'
  export DRL_MULTI_SCENARIO=standard
  export DRL_MULTI_USE_DYNAMIC_REWARD=0
  export DRL_MULTI_USE_DISTANCE_WEIGHTED_REWARD=0
  export DRL_MULTI_USE_LOCAL_CRITIC=0
  export DRL_MULTI_USE_LOCAL_NAVIGATION_REWARD=0
  export DRL_MULTI_USE_WALL_CLEARANCE_REWARD=0
  export DRL_MULTI_BEST_METRIC=full_success
  export DRL_MULTI_EVAL_EPISODES='${DRL_MULTI_EVAL_EPISODES:-40}'
  export DRL_MULTI_MAX_EPOCHS='${DRL_MULTI_MAX_EPOCHS:-12}'
  export DRL_MULTI_EXPL_NOISE='${DRL_MULTI_EXPL_NOISE:-0.05}'
  export DRL_MULTI_EXPL_MIN='${DRL_MULTI_EXPL_MIN:-0.02}'
  export DRL_MULTI_ACTOR_LR='${DRL_MULTI_ACTOR_LR:-0.000005}'
  export DRL_MULTI_CRITIC_LR='${DRL_MULTI_CRITIC_LR:-0.00006}'
  export DRL_MULTI_ACTOR_UPDATE_DELAY_STEPS='${DRL_MULTI_ACTOR_UPDATE_DELAY_STEPS:-20000}'
  export DRL_MULTI_TRAINING_VERSION='stage2-to-3a-shared-policy-from-2d-gentle-guarded-v1'
  export DRL_MULTI_TRAIN_FILE_NAME='$MODEL_NAME'
  export DRL_MULTI_LOAD_MODEL=1
  export DRL_MULTI_LOAD_ACTOR_ONLY=1
  export DRL_MULTI_LOAD_MODEL_NAME='$LOAD_MODEL_NAME'
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u train_velodyne_td3_multi.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached guarded stage2-to-3A shared-policy training started."
echo "PID: $(cat "$PID_FILE")"
echo "Agents: $NUM_AGENTS"
echo "Model: $MODEL_NAME"
echo "Warm start: $LOAD_MODEL_NAME"
echo "Warm start mode: actor only"
echo "Launch: $LAUNCH_PATH"
echo "Dynamic reward: 0"
echo "Distance-weighted reward: 0"
echo "Local critic: 0"
echo "Actor update delay steps: ${DRL_MULTI_ACTOR_UPDATE_DELAY_STEPS:-20000}"
echo "Actor LR: ${DRL_MULTI_ACTOR_LR:-0.000005}"
echo "Exploration noise: ${DRL_MULTI_EXPL_NOISE:-0.05}"
echo "Max epochs: ${DRL_MULTI_MAX_EPOCHS:-12}"
echo "Eval episodes: ${DRL_MULTI_EVAL_EPISODES:-40}"
echo "Log: $log_file"
