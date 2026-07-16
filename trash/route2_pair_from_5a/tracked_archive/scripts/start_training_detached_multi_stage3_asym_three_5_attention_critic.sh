#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$PROJECT_ROOT/.train_multi_stage3_asym_three_5_attention_critic.pid"
NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-5}"
STAGE="stage3_asym_three_5"
LAUNCHFILE="multi_robot_scenario_curriculum_${STAGE}_${NUM_AGENTS}.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCHFILE"
MODEL_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage3_asym_three_5_attention_critic_from_pair}"
LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5a_cleanstart_v2_best}"
CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage3_asym_three_5_cases.json"
ROS_PORT="${DRL_MULTI_ROS_PORT:-12591}"
GAZEBO_PORT="${DRL_MULTI_GAZEBO_PORT:-12691}"

mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/train_multi_${STAGE}_attention_critic_detached_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached attention-critic training process is already running with PID $old_pid"
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
  echo "Please stop it before starting attention-critic training."
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
  export DRL_MULTI_SCENARIO=curriculum
  export DRL_MULTI_CURRICULUM_CASES='$CASES_PATH'
  export DRL_MULTI_CURRICULUM_SAMPLING='${DRL_MULTI_CURRICULUM_SAMPLING:-cycle}'
  export DRL_MULTI_USE_DYNAMIC_REWARD='${DRL_MULTI_USE_DYNAMIC_REWARD:-1}'
  export DRL_MULTI_REWARD_MODE='${DRL_MULTI_REWARD_MODE:-average_plus_interaction}'
  export DRL_MULTI_REWARD_SELF_WEIGHT='${DRL_MULTI_REWARD_SELF_WEIGHT:-0.85}'
  export DRL_MULTI_USE_DISTANCE_WEIGHTED_REWARD='${DRL_MULTI_USE_DISTANCE_WEIGHTED_REWARD:-1}'
  export DRL_MULTI_INTERACTION_SAFE_DISTANCE='${DRL_MULTI_INTERACTION_SAFE_DISTANCE:-0.9}'
  export DRL_MULTI_INTERACTION_CLOSE_PENALTY='${DRL_MULTI_INTERACTION_CLOSE_PENALTY:-0.35}'
  export DRL_MULTI_INTERACTION_STAGNATION_PENALTY='${DRL_MULTI_INTERACTION_STAGNATION_PENALTY:-0.02}'
  export DRL_MULTI_USE_LOCAL_CRITIC=1
  export DRL_MULTI_USE_ATTENTION_CRITIC=1
  export DRL_MULTI_USE_JOINT_ACTION_CRITIC='${DRL_MULTI_USE_JOINT_ACTION_CRITIC:-1}'
  export DRL_MULTI_LOCAL_CRITIC_GEOMETRY_ONLY='${DRL_MULTI_LOCAL_CRITIC_GEOMETRY_ONLY:-0}'
  export DRL_MULTI_LOCAL_CRITIC_MAX_AGENTS='${DRL_MULTI_LOCAL_CRITIC_MAX_AGENTS:-10}'
  export DRL_MULTI_ATTENTION_HIDDEN_DIM='${DRL_MULTI_ATTENTION_HIDDEN_DIM:-128}'
  export DRL_MULTI_ACTIVE_NEIGHBORS_ONLY=1
  export DRL_MULTI_USE_LOCAL_NAVIGATION_REWARD='${DRL_MULTI_USE_LOCAL_NAVIGATION_REWARD:-1}'
  export DRL_MULTI_LOCAL_NAV_HEADING_WEIGHT='${DRL_MULTI_LOCAL_NAV_HEADING_WEIGHT:-0.35}'
  export DRL_MULTI_LOCAL_NAV_WRONG_WAY_PENALTY='${DRL_MULTI_LOCAL_NAV_WRONG_WAY_PENALTY:-0.25}'
  export DRL_MULTI_LOCAL_NAV_TURN_WEIGHT='${DRL_MULTI_LOCAL_NAV_TURN_WEIGHT:-0.22}'
  export DRL_MULTI_LOCAL_NAV_NEAR_GOAL_DISTANCE='${DRL_MULTI_LOCAL_NAV_NEAR_GOAL_DISTANCE:-0.9}'
  export DRL_MULTI_LOCAL_NAV_HEADING_ERROR='${DRL_MULTI_LOCAL_NAV_HEADING_ERROR:-0.5}'
  export DRL_MULTI_USE_WALL_CLEARANCE_REWARD='${DRL_MULTI_USE_WALL_CLEARANCE_REWARD:-0}'
  export DRL_MULTI_BEST_METRIC='${DRL_MULTI_BEST_METRIC:-full_success}'
  export DRL_MULTI_EVAL_EPISODES='${DRL_MULTI_EVAL_EPISODES:-24}'
  export DRL_MULTI_MAX_EPOCHS='${DRL_MULTI_MAX_EPOCHS:-5}'
  export DRL_MULTI_EXPL_NOISE='${DRL_MULTI_EXPL_NOISE:-0.015}'
  export DRL_MULTI_EXPL_MIN='${DRL_MULTI_EXPL_MIN:-0.005}'
  export DRL_MULTI_ACTOR_LR='${DRL_MULTI_ACTOR_LR:-0.0000008}'
  export DRL_MULTI_CRITIC_LR='${DRL_MULTI_CRITIC_LR:-0.00002}'
  export DRL_MULTI_ACTOR_UPDATE_DELAY_STEPS='${DRL_MULTI_ACTOR_UPDATE_DELAY_STEPS:-4000}'
  export DRL_MULTI_POLICY_FREQ='${DRL_MULTI_POLICY_FREQ:-2}'
  export DRL_MULTI_ACTOR_ANCHOR_WEIGHT='${DRL_MULTI_ACTOR_ANCHOR_WEIGHT:-0.0}'
  export DRL_MULTI_TRAINING_VERSION='stage3-asym-three-5-attention-critic-v1'
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

echo "Detached attention-critic training started."
echo "PID: $(cat "$PID_FILE")"
echo "Stage: $STAGE"
echo "Agents: $NUM_AGENTS"
echo "Model: $MODEL_NAME"
echo "Warm start: $LOAD_MODEL_NAME"
echo "Warm start mode: actor only"
echo "Cases: $CASES_PATH"
echo "Launch: $LAUNCH_PATH"
echo "Attention critic: enabled"
echo "Joint-action critic: ${DRL_MULTI_USE_JOINT_ACTION_CRITIC:-1}"
echo "Attention hidden dim: ${DRL_MULTI_ATTENTION_HIDDEN_DIM:-128}"
echo "Max epochs: ${DRL_MULTI_MAX_EPOCHS:-5}"
echo "Eval episodes: ${DRL_MULTI_EVAL_EPISODES:-24}"
echo "Log: $log_file"
