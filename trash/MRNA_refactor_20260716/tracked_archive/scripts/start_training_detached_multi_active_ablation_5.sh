#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
NUM_AGENTS=5
VARIANT="${1:-weighted09_active}"
ROS_PORT="${DRL_MULTI_ROS_PORT:-11367}"
GAZEBO_PORT="${DRL_MULTI_GAZEBO_PORT:-11407}"
ANTI_STAGNATION_REWARD=0
ANTI_STAGNATION_PENALTY=0.0
ANTI_STAGNATION_LINEAR_THRESHOLD=0.05
ANTI_STAGNATION_PROGRESS_THRESHOLD=0.005
ANTI_STAGNATION_MIN_LASER=0.35

case "$VARIANT" in
  weighted08_active)
    MODEL_NAME="TD3_velodyne_multi_v4_weighted08_active_5"
    VERSION="multi-agent-weighted08-active-neighbors-5-v1"
    USE_DYNAMIC_REWARD=1
    REWARD_MODE=average
    SELF_WEIGHT=0.8
    USE_DISTANCE_WEIGHTED_REWARD=1
    INTERACTION_SAFE_DISTANCE=1.2
    INTERACTION_CLOSE_PENALTY=0.5
    INTERACTION_STAGNATION_PENALTY=0.05
    USE_LOCAL_CRITIC=0
    LOCAL_CRITIC_GEOMETRY_ONLY=0
    DESCRIPTION="distance-weighted 0.8 own + 0.2 active-neighbor"
    ;;
  weighted09_active)
    MODEL_NAME="TD3_velodyne_multi_v4_weighted09_active_5"
    VERSION="multi-agent-weighted09-active-neighbors-5-v1"
    USE_DYNAMIC_REWARD=1
    REWARD_MODE=average
    SELF_WEIGHT=0.9
    USE_DISTANCE_WEIGHTED_REWARD=1
    INTERACTION_SAFE_DISTANCE=1.2
    INTERACTION_CLOSE_PENALTY=0.5
    INTERACTION_STAGNATION_PENALTY=0.05
    USE_LOCAL_CRITIC=0
    LOCAL_CRITIC_GEOMETRY_ONLY=0
    DESCRIPTION="distance-weighted 0.9 own + 0.1 active-neighbor"
    ;;
  weighted095_active)
    MODEL_NAME="TD3_velodyne_multi_v4_weighted095_active_5"
    VERSION="multi-agent-weighted095-active-neighbors-5-v1"
    USE_DYNAMIC_REWARD=1
    REWARD_MODE=average
    SELF_WEIGHT=0.95
    USE_DISTANCE_WEIGHTED_REWARD=1
    INTERACTION_SAFE_DISTANCE=1.2
    INTERACTION_CLOSE_PENALTY=0.5
    INTERACTION_STAGNATION_PENALTY=0.05
    USE_LOCAL_CRITIC=0
    LOCAL_CRITIC_GEOMETRY_ONLY=0
    DESCRIPTION="distance-weighted 0.95 own + 0.05 active-neighbor"
    ;;
  interaction_only_active)
    MODEL_NAME="TD3_velodyne_multi_v4_interaction_only_active_5"
    VERSION="multi-agent-interaction-only-active-neighbors-5-v1"
    USE_DYNAMIC_REWARD=1
    REWARD_MODE=interaction_only
    SELF_WEIGHT=
    USE_DISTANCE_WEIGHTED_REWARD=0
    INTERACTION_SAFE_DISTANCE=1.2
    INTERACTION_CLOSE_PENALTY=0.5
    INTERACTION_STAGNATION_PENALTY=0.05
    USE_LOCAL_CRITIC=0
    LOCAL_CRITIC_GEOMETRY_ONLY=0
    DESCRIPTION="individual reward + active-neighbor interaction penalty"
    ;;
  individual_active_probe)
    MODEL_NAME="TD3_velodyne_multi_v4_individual_active_probe_5"
    VERSION="multi-agent-individual-active-probe-5-v1"
    USE_DYNAMIC_REWARD=1
    REWARD_MODE=interaction_only
    SELF_WEIGHT=
    USE_DISTANCE_WEIGHTED_REWARD=0
    INTERACTION_SAFE_DISTANCE=1.2
    INTERACTION_CLOSE_PENALTY=0.0
    INTERACTION_STAGNATION_PENALTY=0.0
    USE_LOCAL_CRITIC=0
    LOCAL_CRITIC_GEOMETRY_ONLY=0
    DESCRIPTION="individual reward through active-neighbor diagnostics"
    ;;
  individual_antistagnation)
    MODEL_NAME="TD3_velodyne_multi_v4_individual_antistagnation_5"
    VERSION="multi-agent-individual-antistagnation-5-v1"
    USE_DYNAMIC_REWARD=1
    REWARD_MODE=interaction_only
    SELF_WEIGHT=
    USE_DISTANCE_WEIGHTED_REWARD=0
    INTERACTION_SAFE_DISTANCE=1.2
    INTERACTION_CLOSE_PENALTY=0.0
    INTERACTION_STAGNATION_PENALTY=0.0
    ANTI_STAGNATION_REWARD=1
    ANTI_STAGNATION_PENALTY=0.2
    ANTI_STAGNATION_LINEAR_THRESHOLD=0.05
    ANTI_STAGNATION_PROGRESS_THRESHOLD=0.005
    ANTI_STAGNATION_MIN_LASER=0.35
    USE_LOCAL_CRITIC=0
    LOCAL_CRITIC_GEOMETRY_ONLY=0
    DESCRIPTION="individual reward + self anti-stagnation penalty"
    ;;
  geo_individual_active)
    MODEL_NAME="TD3_velodyne_multi_v4_local_critic_geo_individual_active_5"
    VERSION="multi-agent-local-neighborhood-critic-geo-individual-active-5-v1"
    USE_DYNAMIC_REWARD=0
    REWARD_MODE=average
    SELF_WEIGHT=
    USE_DISTANCE_WEIGHTED_REWARD=0
    INTERACTION_SAFE_DISTANCE=1.2
    INTERACTION_CLOSE_PENALTY=0.5
    INTERACTION_STAGNATION_PENALTY=0.05
    USE_LOCAL_CRITIC=1
    LOCAL_CRITIC_GEOMETRY_ONLY=1
    DESCRIPTION="individual reward + active-neighbor geometry critic"
    ;;
  geo_weighted09_active)
    MODEL_NAME="TD3_velodyne_multi_v4_local_critic_geo_weighted09_active_5"
    VERSION="multi-agent-local-neighborhood-critic-geo-weighted09-active-5-v1"
    USE_DYNAMIC_REWARD=1
    REWARD_MODE=average
    SELF_WEIGHT=0.9
    USE_DISTANCE_WEIGHTED_REWARD=1
    INTERACTION_SAFE_DISTANCE=1.2
    INTERACTION_CLOSE_PENALTY=0.5
    INTERACTION_STAGNATION_PENALTY=0.05
    USE_LOCAL_CRITIC=1
    LOCAL_CRITIC_GEOMETRY_ONLY=1
    DESCRIPTION="distance-weighted 0.9 own + 0.1 active-neighbor with geometry critic"
    ;;
  *)
    echo "Unknown variant: $VARIANT"
    echo "Available variants:"
    echo "  weighted08_active"
    echo "  weighted09_active"
    echo "  weighted095_active"
    echo "  interaction_only_active"
    echo "  individual_active_probe"
    echo "  individual_antistagnation"
    echo "  geo_individual_active"
    echo "  geo_weighted09_active"
    exit 1
    ;;
esac

LAUNCHFILE="multi_robot_scenario_${VARIANT}_${NUM_AGENTS}.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCHFILE"
PID_FILE="$PROJECT_ROOT/.train_multi_${VARIANT}_5_detached.pid"

mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/train_multi_${VARIANT}_5_detached_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached 5-agent $VARIANT training process is already running with PID $old_pid"
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
  echo "Please stop the current multi-agent training before starting $VARIANT detached mode."
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
  export DRL_MULTI_USE_DYNAMIC_REWARD='$USE_DYNAMIC_REWARD'
  export DRL_MULTI_REWARD_MODE='$REWARD_MODE'
  export DRL_MULTI_REWARD_SELF_WEIGHT='$SELF_WEIGHT'
  export DRL_MULTI_USE_DISTANCE_WEIGHTED_REWARD='$USE_DISTANCE_WEIGHTED_REWARD'
  export DRL_MULTI_REWARD_SIGMA=2.0
  export DRL_MULTI_INTERACTION_SAFE_DISTANCE='$INTERACTION_SAFE_DISTANCE'
  export DRL_MULTI_INTERACTION_CLOSE_PENALTY='$INTERACTION_CLOSE_PENALTY'
  export DRL_MULTI_INTERACTION_STAGNATION_PENALTY='$INTERACTION_STAGNATION_PENALTY'
  export DRL_MULTI_USE_ANTI_STAGNATION_REWARD='$ANTI_STAGNATION_REWARD'
  export DRL_MULTI_ANTI_STAGNATION_PENALTY='$ANTI_STAGNATION_PENALTY'
  export DRL_MULTI_ANTI_STAGNATION_LINEAR_THRESHOLD='$ANTI_STAGNATION_LINEAR_THRESHOLD'
  export DRL_MULTI_ANTI_STAGNATION_PROGRESS_THRESHOLD='$ANTI_STAGNATION_PROGRESS_THRESHOLD'
  export DRL_MULTI_ANTI_STAGNATION_MIN_LASER='$ANTI_STAGNATION_MIN_LASER'
  export DRL_MULTI_USE_LOCAL_CRITIC='$USE_LOCAL_CRITIC'
  export DRL_MULTI_LOCAL_CRITIC_GEOMETRY_ONLY='$LOCAL_CRITIC_GEOMETRY_ONLY'
  export DRL_MULTI_LOCAL_CRITIC_MAX_AGENTS=10
  export DRL_MULTI_ACTIVE_NEIGHBORS_ONLY=1
  export DRL_MULTI_BEST_METRIC=full_success
  export DRL_MULTI_EVAL_EPISODES=\"\${DRL_MULTI_EVAL_EPISODES:-20}\"
  export DRL_MULTI_MAX_EPOCHS=\"\${DRL_MULTI_MAX_EPOCHS:-20}\"
  export DRL_MULTI_TRAINING_VERSION='$VERSION'
  export DRL_MULTI_TRAIN_FILE_NAME='$MODEL_NAME'
  export DRL_MULTI_LOAD_MODEL=1
  export DRL_MULTI_LOAD_MODEL_NAME='TD3_velodyne_multi_v4'
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u train_velodyne_td3_multi.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached 5-agent active-neighbor ablation training started."
echo "Variant: $VARIANT"
echo "PID: $(cat "$PID_FILE")"
echo "Model: $MODEL_NAME"
echo "Launch: $LAUNCH_PATH"
echo "Warm start: TD3_velodyne_multi_v4"
echo "Reward/Critic: $DESCRIPTION"
echo "Reward mode: $REWARD_MODE"
echo "Active neighbors only: enabled"
echo "Anti-stagnation reward: $ANTI_STAGNATION_REWARD"
echo "Anti-stagnation penalty: $ANTI_STAGNATION_PENALTY"
echo "Best metric: full_success"
echo "Max epochs: ${DRL_MULTI_MAX_EPOCHS:-20}"
echo "Log: $log_file"
