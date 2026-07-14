#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export DRL_MULTI_TRAIN_FILE_NAME="${DRL_MULTI_TRAIN_FILE_NAME:-TD3_multi_dense5_from_5d_geo}"
export DRL_MULTI_LOAD_MODEL_NAME="${DRL_MULTI_LOAD_MODEL_NAME:-TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best}"
export DRL_MULTI_LOAD_ACTOR_ONLY="${DRL_MULTI_LOAD_ACTOR_ONLY:-0}"
export DRL_MULTI_RESUME_TRAINING="${DRL_MULTI_RESUME_TRAINING:-0}"
export DRL_MULTI_TRAINING_VERSION="${DRL_MULTI_TRAINING_VERSION:-dense5-from-5d-geo-v2}"
export DRL_MULTI_ROS_PORT="${DRL_MULTI_ROS_PORT:-13621}"
export DRL_MULTI_GAZEBO_PORT="${DRL_MULTI_GAZEBO_PORT:-13721}"

exec "$PROJECT_ROOT/scripts/start_training_detached_multi_curriculum.sh" stage4_asym_dense_5
