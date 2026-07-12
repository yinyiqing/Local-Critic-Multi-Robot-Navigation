#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

STANDARD_ACTOR="${DRL_MULTI_STANDARD_ACTOR_FILE:-TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best}"
DENSE_ACTOR="${DRL_MULTI_DENSE_ACTOR_FILE:-TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5a_cleanstart_v2_best}"
SWITCH_TAG="${DRL_MULTI_TEST_LOG_TAG:-DUAL}"
TARGET_EPISODES="${DRL_MULTI_TEST_TARGET_EPISODES:-120}"

export DRL_MULTI_TEST_FILE_NAME="$STANDARD_ACTOR"
export DRL_MULTI_STANDARD_ACTOR_FILE="$STANDARD_ACTOR"
export DRL_MULTI_DENSE_ACTOR_FILE="$DENSE_ACTOR"
export DRL_MULTI_TEST_LOG_TAG="$SWITCH_TAG"
export DRL_MULTI_TEST_TARGET_EPISODES="$TARGET_EPISODES"
export DRL_MULTI_TEST_STATE_PATH="./checkpoints/dual_std5_test_state.pt"
export DRL_MULTI_TEST_STATS_PATH="./results/dual_std5_test.npy"

bash "$PROJECT_ROOT/scripts/start_test_detached_multi_stage2_to_5a_shared_guarded_best.sh"
