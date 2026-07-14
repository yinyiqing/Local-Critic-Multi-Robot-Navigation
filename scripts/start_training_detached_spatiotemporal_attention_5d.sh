#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="${DRL_ATTENTION_LOG_DIR:-$PROJECT_ROOT/experiments/04_保留专门化/03_门控注意力增强/logs/train}"
PID_FILE="$PROJECT_ROOT/.train_spatiotemporal_attention_5d_detached.pid"
LAUNCHFILE="multi_robot_scenario_attention_5.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCHFILE"
CASES_PATH="${DRL_ATTENTION_CASES_PATH:-$PROJECT_ROOT/experiments/02_课程学习/cases/stage4_spatiotemporal_attention_mixed_asym_dense_5_cases.json}"
BASE_MODEL="${DRL_ATTENTION_BASE_MODEL:-TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best}"
MODEL_NAME="${DRL_ATTENTION_MODEL_NAME:-TD3_velodyne_multi_v5_attention_residual_from_5d_asym_dense_correction_v2}"
ROS_PORT="${DRL_ATTENTION_ROS_PORT:-12821}"
GAZEBO_PORT="${DRL_ATTENTION_GAZEBO_PORT:-12921}"

if [[ ! -f "$TD3_DIR/pytorch_models/${BASE_MODEL}_actor.pth" ]]; then
  echo "Missing frozen base actor: $TD3_DIR/pytorch_models/${BASE_MODEL}_actor.pth"
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(<"$PID_FILE")"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "Attention training is already running with PID $old_pid"
    exit 1
  fi
fi

existing_pid="$(pgrep -af '^python3(\.8)? .*train_.*td3_multi\.py$|^python3(\.8)? .*train_spatiotemporal_attention\.py$' | awk 'NR==1 {print $1}' || true)"
if [[ -n "$existing_pid" ]]; then
  echo "Another multi-agent training process is already running with PID $existing_pid"
  exit 1
fi

mkdir -p "$LOG_DIR"
python3 "$PROJECT_ROOT/scripts/generate_multi_robot_launch.py" \
  --num-agents 5 \
  --output "$LAUNCH_PATH"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/train_spatiotemporal_attention_5d_${timestamp}.log"

setsid bash -lc "
  source /opt/ros/noetic/setup.bash
  source '$PROJECT_ROOT/env.python.sh'
  export ROS_HOSTNAME=localhost
  export ROS_MASTER_URI=http://localhost:${ROS_PORT}
  export ROS_PORT_SIM=${ROS_PORT}
  export GAZEBO_MASTER_URI=http://localhost:${GAZEBO_PORT}
  export GAZEBO_RESOURCE_PATH='$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch'
  export DRL_MULTI_CURRICULUM_CASES='$CASES_PATH'
  export DRL_MULTI_CURRICULUM_SAMPLING=random
  export DRL_ATTENTION_LAUNCHFILE='$LAUNCHFILE'
  export DRL_ATTENTION_BASE_MODEL='$BASE_MODEL'
  export DRL_ATTENTION_MODEL_NAME='$MODEL_NAME'
  export DRL_ATTENTION_STANDARD_GROUP='${DRL_ATTENTION_STANDARD_GROUP:-standard}'
  export DRL_ATTENTION_DENSE_GROUP='${DRL_ATTENTION_DENSE_GROUP:-dense}'
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u train_spatiotemporal_attention.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"
echo "Spatiotemporal attention training started."
echo "PID: $(<"$PID_FILE")"
echo "Frozen base actor: $BASE_MODEL"
echo "Attention model: $MODEL_NAME"
echo "Curriculum: $CASES_PATH"
echo "ROS/Gazebo ports: $ROS_PORT / $GAZEBO_PORT"
echo "Log: $log_file"
