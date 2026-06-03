#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
STAGE="${1:-stage1_single}"
ROS_PORT="${DRL_MULTI_ROS_PORT:-11367}"
GAZEBO_PORT="${DRL_MULTI_GAZEBO_PORT:-11407}"

case "$STAGE" in
  stage1_single)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    MODEL_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage1_single}"
    LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4}"
    CASES_PATH="$PROJECT_ROOT/experiments/多智能体/课程学习/cases/stage1_single_local_cases.json"
    VERSION="multi-agent-curriculum-stage1-single-local-v1"
    DEFAULT_MAX_EPOCHS=8
    DEFAULT_EVAL_EPISODES=24
    DEFAULT_EXPL_NOISE=0.45
    DEFAULT_EXPL_MIN=0.08
    DEFAULT_ACTOR_LR=0.0005
    DEFAULT_CRITIC_LR=0.0005
    ;;
  stage1b_single)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    MODEL_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage1b_single}"
    LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage1_single_best}"
    CASES_PATH="$PROJECT_ROOT/experiments/多智能体/课程学习/cases/stage1b_single_near_goal_sidewall_cases.json"
    VERSION="multi-agent-curriculum-stage1b-near-goal-sidewall-v1"
    DEFAULT_MAX_EPOCHS=8
    DEFAULT_EVAL_EPISODES=32
    DEFAULT_EXPL_NOISE=0.28
    DEFAULT_EXPL_MIN=0.06
    DEFAULT_ACTOR_LR=0.0002
    DEFAULT_CRITIC_LR=0.0002
    ;;
  stage1b_hard_only)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    MODEL_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage1b_hard_only}"
    LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage1b_single_best}"
    CASES_PATH="$PROJECT_ROOT/experiments/多智能体/课程学习/cases/stage1b_hard_only_cases.json"
    VERSION="multi-agent-curriculum-stage1b-hard-only-v1"
    DEFAULT_MAX_EPOCHS=6
    DEFAULT_EVAL_EPISODES=32
    DEFAULT_EXPL_NOISE=0.16
    DEFAULT_EXPL_MIN=0.04
    DEFAULT_ACTOR_LR=0.0001
    DEFAULT_CRITIC_LR=0.0001
    ;;
  stage1c_wall_clearance)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    MODEL_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage1c_wall_clearance}"
    LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage1b_single_best}"
    CASES_PATH="$PROJECT_ROOT/experiments/多智能体/课程学习/cases/stage1c_wall_clearance_cases.json"
    VERSION="multi-agent-curriculum-stage1c-wall-clearance-v1"
    DEFAULT_MAX_EPOCHS=10
    DEFAULT_EVAL_EPISODES=48
    DEFAULT_EXPL_NOISE=0.10
    DEFAULT_EXPL_MIN=0.03
    DEFAULT_ACTOR_LR=0.00005
    DEFAULT_CRITIC_LR=0.00005
    ;;
  stage2_dense)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-5}"
    MODEL_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage2_dense_5}"
    LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage1_single_best}"
    CASES_PATH="$PROJECT_ROOT/experiments/多智能体/课程学习/cases/stage2_dense_multi_cases.json"
    VERSION="multi-agent-curriculum-stage2-dense-v1"
    DEFAULT_MAX_EPOCHS=8
    DEFAULT_EVAL_EPISODES=24
    DEFAULT_EXPL_NOISE=0.35
    DEFAULT_EXPL_MIN=0.08
    DEFAULT_ACTOR_LR=0.0003
    DEFAULT_CRITIC_LR=0.0003
    ;;
  stage2_three_dense)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-3}"
    MODEL_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage2_three_dense_3}"
    LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage1_single_best}"
    CASES_PATH="$PROJECT_ROOT/experiments/多智能体/课程学习/cases/stage2_three_dense_cases.json"
    VERSION="multi-agent-curriculum-stage2-three-dense-v1"
    DEFAULT_MAX_EPOCHS=8
    DEFAULT_EVAL_EPISODES=24
    DEFAULT_EXPL_NOISE=0.32
    DEFAULT_EXPL_MIN=0.08
    DEFAULT_ACTOR_LR=0.0003
    DEFAULT_CRITIC_LR=0.0003
    ;;
  *)
    echo "Unknown curriculum stage: $STAGE"
    echo "Available stages: stage1_single, stage1b_single, stage1b_hard_only, stage1c_wall_clearance, stage2_three_dense, stage2_dense"
    exit 1
    ;;
esac

LAUNCHFILE="multi_robot_scenario_curriculum_${STAGE}_${NUM_AGENTS}.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCHFILE"
PID_FILE="$PROJECT_ROOT/.train_multi_curriculum_${STAGE}_detached.pid"
CURRICULUM_SAMPLING="${DRL_MULTI_CURRICULUM_SAMPLING:-cycle}"
EVAL_EPISODES="${DRL_MULTI_EVAL_EPISODES:-$DEFAULT_EVAL_EPISODES}"
MAX_EPOCHS="${DRL_MULTI_MAX_EPOCHS:-$DEFAULT_MAX_EPOCHS}"
EXPL_NOISE="${DRL_MULTI_EXPL_NOISE:-$DEFAULT_EXPL_NOISE}"
EXPL_MIN="${DRL_MULTI_EXPL_MIN:-$DEFAULT_EXPL_MIN}"
ACTOR_LR="${DRL_MULTI_ACTOR_LR:-$DEFAULT_ACTOR_LR}"
CRITIC_LR="${DRL_MULTI_CRITIC_LR:-$DEFAULT_CRITIC_LR}"
if [[ "$STAGE" == "stage1c_wall_clearance" ]]; then
  WALL_CLEARANCE_REWARD="${DRL_MULTI_USE_WALL_CLEARANCE_REWARD:-1}"
else
  WALL_CLEARANCE_REWARD="${DRL_MULTI_USE_WALL_CLEARANCE_REWARD:-0}"
fi
WALL_CLEARANCE_SAFE_DISTANCE="${DRL_MULTI_WALL_CLEARANCE_SAFE_DISTANCE:-0.75}"
WALL_CLEARANCE_PENALTY="${DRL_MULTI_WALL_CLEARANCE_PENALTY:-1.5}"
WALL_CLEARANCE_SPEED_WEIGHT="${DRL_MULTI_WALL_CLEARANCE_SPEED_WEIGHT:-0.8}"
WALL_CLEARANCE_TURN_WEIGHT="${DRL_MULTI_WALL_CLEARANCE_TURN_WEIGHT:-0.4}"

mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/train_multi_curriculum_${STAGE}_detached_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached curriculum training process is already running with PID $old_pid"
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
  echo "Please stop it before starting curriculum stage $STAGE."
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
  export DRL_MULTI_CURRICULUM_SAMPLING='$CURRICULUM_SAMPLING'
  export DRL_MULTI_USE_DYNAMIC_REWARD=0
  export DRL_MULTI_USE_LOCAL_CRITIC=0
  export DRL_MULTI_ACTIVE_NEIGHBORS_ONLY=1
  export DRL_MULTI_USE_WALL_CLEARANCE_REWARD='$WALL_CLEARANCE_REWARD'
  export DRL_MULTI_WALL_CLEARANCE_SAFE_DISTANCE='$WALL_CLEARANCE_SAFE_DISTANCE'
  export DRL_MULTI_WALL_CLEARANCE_PENALTY='$WALL_CLEARANCE_PENALTY'
  export DRL_MULTI_WALL_CLEARANCE_SPEED_WEIGHT='$WALL_CLEARANCE_SPEED_WEIGHT'
  export DRL_MULTI_WALL_CLEARANCE_TURN_WEIGHT='$WALL_CLEARANCE_TURN_WEIGHT'
  export DRL_MULTI_BEST_METRIC=full_success
  export DRL_MULTI_EVAL_EPISODES='$EVAL_EPISODES'
  export DRL_MULTI_MAX_EPOCHS='$MAX_EPOCHS'
  export DRL_MULTI_EXPL_NOISE='$EXPL_NOISE'
  export DRL_MULTI_EXPL_MIN='$EXPL_MIN'
  export DRL_MULTI_ACTOR_LR='$ACTOR_LR'
  export DRL_MULTI_CRITIC_LR='$CRITIC_LR'
  export DRL_MULTI_TRAINING_VERSION='$VERSION'
  export DRL_MULTI_TRAIN_FILE_NAME='$MODEL_NAME'
  export DRL_MULTI_LOAD_MODEL=1
  export DRL_MULTI_LOAD_MODEL_NAME='$LOAD_MODEL_NAME'
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u train_velodyne_td3_multi.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached curriculum training started."
echo "Stage: $STAGE"
echo "PID: $(cat "$PID_FILE")"
echo "Agents: $NUM_AGENTS"
echo "Model: $MODEL_NAME"
echo "Warm start: $LOAD_MODEL_NAME"
echo "Cases: $CASES_PATH"
echo "Launch: $LAUNCH_PATH"
echo "Sampling: $CURRICULUM_SAMPLING"
echo "Max epochs: $MAX_EPOCHS"
echo "Eval episodes: $EVAL_EPISODES"
echo "Exploration noise: $EXPL_NOISE"
echo "Actor LR: $ACTOR_LR"
echo "Critic LR: $CRITIC_LR"
echo "Wall-clearance reward: $WALL_CLEARANCE_REWARD"
echo "Wall-clearance safe distance: $WALL_CLEARANCE_SAFE_DISTANCE"
echo "Wall-clearance penalty: $WALL_CLEARANCE_PENALTY"
echo "Log: $log_file"
