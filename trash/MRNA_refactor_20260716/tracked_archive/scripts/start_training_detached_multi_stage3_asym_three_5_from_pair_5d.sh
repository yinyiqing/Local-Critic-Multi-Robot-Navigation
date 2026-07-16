#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export DRL_MULTI_TRAIN_FILE_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_velodyne_multi_v4_curriculum_stage3_asym_three_5_from_pair_5d}"
export DRL_MULTI_LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5d_best}"
export DRL_MULTI_LOAD_ACTOR_ONLY="${DRL_MULTI_LOAD_ACTOR_ONLY:-0}"
export DRL_MULTI_TRAINING_VERSION="${DRL_MULTI_TRAINING_VERSION:-multi-agent-curriculum-stage3-asym-three-5-from-pair-5d-v1}"
export DRL_MULTI_ROS_PORT="${DRL_MULTI_ROS_PORT:-12641}"
export DRL_MULTI_GAZEBO_PORT="${DRL_MULTI_GAZEBO_PORT:-12741}"

exec "$PROJECT_ROOT/scripts/start_training_detached_multi_curriculum.sh" stage3_asym_three_5
