#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"
LOG_DIR="$PROJECT_ROOT/logs"
CUSTOM_LOG_DIR="${DRL_MULTI_TEST_LOG_DIR:-}"
STAGE="${1:-stage1_single}"
MODEL_NAME="${2:-}"
ROS_PORT="${DRL_MULTI_TEST_ROS_PORT:-11368}"
GAZEBO_PORT="${DRL_MULTI_TEST_GAZEBO_PORT:-11408}"
TARGET_EPISODES="${DRL_MULTI_TEST_TARGET_EPISODES:-120}"

case "$STAGE" in
  stage1_single)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage1_single_local_cases.json"
    ;;
  stage1b_single)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage1_single_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage1b_single_near_goal_sidewall_cases.json"
    ;;
  stage1e_single_rescue)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage1e_single_rescue_from_stage1_single_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage1e_single_rescue_cases.json"
    ;;
  stage1f_wall_parallel_rescue)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage1f_wall_parallel_rescue_from_stage1e_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage1f_wall_parallel_rescue_cases.json"
    ;;
  stage1g_collision_guard)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage1g_collision_guard_cases.json"
    ;;
  stage1h_separated_reverse_guard)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage1h_separated_reverse_guard_from_stage1g_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage1h_separated_reverse_guard_cases.json"
    ;;
  stage1i_yaw_reverse_collision_guard)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-1}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage1i_yaw_reverse_collision_cases.json"
    ;;
  stage2a_manual_dense_crossing)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-3}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage2a_manual_dense_crossing_from_stage1g_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage2a_manual_dense_crossing_cases.json"
    ;;
  stage2_pre_pairwise_warmup)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-2}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage2_pre_pairwise_warmup_from_stage1g_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage2_pre_pairwise_warmup_cases.json"
    ;;
  stage2_pairwise_diagnostic)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-2}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage2_pairwise_diagnostic_cases.json"
    ;;
  stage2b_three_light_dense)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-3}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage2b_three_light_dense_cases.json"
    ;;
  stage2b_three_transition)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-3}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage2b_three_transition_cases.json"
    ;;
  stage2_pairwise_to_dense)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-5}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage2_pairwise_to_dense_from_5a_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage2_pairwise_to_dense_5_cases.json"
    ;;
  stage3_asym_pair_5)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-5}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5d_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage3_asym_pair_5_cases.json"
    ;;
  stage3_asym_three_5)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-5}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage3_asym_three_5_from_pair_5d_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage3_asym_three_5_cases.json"
    ;;
  stage2_dense)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-5}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage2_dense_multi_cases.json"
    ;;
  stage2_three_dense)
    NUM_AGENTS="${DRL_MULTI_NUM_AGENTS:-3}"
    DEFAULT_MODEL="TD3_velodyne_multi_v4_curriculum_stage2_three_dense_3_best"
    CASES_PATH="$PROJECT_ROOT/experiments/02_课程学习/cases/stage2_three_dense_cases.json"
    ;;
  *)
    echo "Unknown curriculum stage: $STAGE"
    echo "Available stages: stage1_single, stage1b_single, stage1e_single_rescue, stage1f_wall_parallel_rescue, stage1g_collision_guard, stage1h_separated_reverse_guard, stage1i_yaw_reverse_collision_guard, stage2_pairwise_diagnostic, stage2_pre_pairwise_warmup, stage2a_manual_dense_crossing, stage2b_three_transition, stage2b_three_light_dense, stage2_pairwise_to_dense, stage2_three_dense, stage2_dense, stage3_asym_pair_5, stage3_asym_three_5"
    exit 1
    ;;
esac

if [[ -z "$MODEL_NAME" ]]; then
  MODEL_NAME="$DEFAULT_MODEL"
fi

LAUNCHFILE="multi_robot_scenario_curriculum_test_${STAGE}_${NUM_AGENTS}.launch"
LAUNCH_PATH="$TD3_DIR/assets/$LAUNCHFILE"
PID_FILE="$PROJECT_ROOT/.test_multi_curriculum_${STAGE}_detached.pid"
CURRICULUM_SAMPLING="${DRL_MULTI_CURRICULUM_SAMPLING:-cycle}"

mkdir -p "$LOG_DIR"
if [[ -n "$CUSTOM_LOG_DIR" ]]; then
  LOG_DIR="$CUSTOM_LOG_DIR"
fi
mkdir -p "$LOG_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
safe_model="${MODEL_NAME//[^A-Za-z0-9_]/_}"
CUSTOM_LOG_TAG="${DRL_MULTI_TEST_LOG_TAG:-}"
STATE_PATH="${DRL_MULTI_TEST_STATE_PATH:-./checkpoints/${safe_model}_${STAGE}_test_state.pt}"
STATS_PATH="${DRL_MULTI_TEST_STATS_PATH:-./results/${safe_model}_${STAGE}_test.npy}"

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
      MODEL_TAG="$safe_model"
      ;;
  esac
fi

log_file="$LOG_DIR/test_${STAGE}_${MODEL_TAG}_${timestamp}.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "A detached curriculum test process is already running with PID $old_pid"
    exit 1
  fi
fi

if [[ ! -f "$TD3_DIR/pytorch_models/${MODEL_NAME}_actor.pth" ]]; then
  echo "Actor model is missing: $TD3_DIR/pytorch_models/${MODEL_NAME}_actor.pth"
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
  export DRL_MULTI_SCENARIO=curriculum
  export DRL_MULTI_CURRICULUM_CASES='$CASES_PATH'
  export DRL_MULTI_CURRICULUM_SAMPLING='$CURRICULUM_SAMPLING'
  cd '$PROJECT_ROOT/catkin_ws'
  source devel_isolated/setup.bash
  cd '$TD3_DIR'
  exec python3 -u test_velodyne_td3_multi.py
" >"$log_file" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Detached curriculum test started."
echo "Stage: $STAGE"
echo "PID: $(cat "$PID_FILE")"
echo "Agents: $NUM_AGENTS"
echo "Model: $MODEL_NAME"
echo "Cases: $CASES_PATH"
echo "Sampling: $CURRICULUM_SAMPLING"
echo "Launch: $LAUNCH_PATH"
echo "Target episodes: $TARGET_EPISODES"
echo "Log: $log_file"
