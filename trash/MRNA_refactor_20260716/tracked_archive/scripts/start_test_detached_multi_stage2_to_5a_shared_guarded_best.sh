#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
CUSTOM_LOG_DIR="${DRL_MULTI_TEST_LOG_DIR:-}"
PID_FILE="$PROJECT_ROOT/.test_multi_stage2_to_5a_shared_guarded_best_detached.pid"
NUM_AGENTS=5
LAUNCHFILE="multi_robot_scenario_stage2_to_5a_shared_guarded_test_${NUM_AGENTS}.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCHFILE"
MODEL_NAME="${DRL_MULTI_TEST_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best}"
ROS_PORT="${DRL_MULTI_ROS_PORT:-11386}"
GAZEBO_PORT="${DRL_MULTI_GAZEBO_PORT:-11486}"
TARGET_EPISODES="${DRL_MULTI_TEST_TARGET_EPISODES:-300}"
SAFE_MODEL="${MODEL_NAME//[^A-Za-z0-9_]/_}"
CUSTOM_LOG_TAG="${DRL_MULTI_TEST_LOG_TAG:-}"
STATE_PATH="${DRL_MULTI_TEST_STATE_PATH:-./checkpoints/${SAFE_MODEL}_standard_5a_guarded_test_state.pt}"
STATS_PATH="${DRL_MULTI_TEST_STATS_PATH:-./results/${SAFE_MODEL}_standard_5a_guarded_test.npy}"

if [[ -n "$CUSTOM_LOG_TAG" ]]; then
  MODEL_TAG="$CUSTOM_LOG_TAG"
else
  case "$MODEL_NAME" in
    TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best)
      MODEL_TAG="5A"
      ;;
    TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best)
      MODEL_TAG="5D"
      ;;
    TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5d_best)
      MODEL_TAG="PAIR_5D"
      ;;
    TD3_velodyne_multi_v4_curriculum_stage3_asym_three_5_from_pair_5d_best)
      MODEL_TAG="THREE_5D"
      ;;
    *)
      MODEL_TAG="$SAFE_MODEL"
      ;;
  esac
fi

mkdir -p "$LOG_DIR"
if [[ -n "$CUSTOM_LOG_DIR" ]]; then
  LOG_DIR="$CUSTOM_LOG_DIR"
fi
mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/test_std5_${MODEL_TAG}_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached stage2-to-5A guarded best-model test process is already running with PID $old_pid"
    exit 1
  fi
fi

if [[ ! -f "$TD3_DIR/pytorch_models/${MODEL_NAME}_actor.pth" ]]; then
  echo "Best actor model is missing: $TD3_DIR/pytorch_models/${MODEL_NAME}_actor.pth"
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
  export DRL_MULTI_TEST_TARGET_EPISODES='$TARGET_EPISODES'
  export DRL_MULTI_TEST_STATE_PATH='$STATE_PATH'
  export DRL_MULTI_TEST_STATS_PATH='$STATS_PATH'
  export DRL_MULTI_SCENARIO=standard
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u test_velodyne_td3_multi.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached stage2-to-5A guarded best-model test started."
echo "PID: $(cat "$PID_FILE")"
echo "Agents: $NUM_AGENTS"
echo "Model: $MODEL_NAME"
echo "Launch: $LAUNCH_PATH"
echo "Scenario: standard"
echo "Target episodes: $TARGET_EPISODES"
echo "Log: $log_file"
