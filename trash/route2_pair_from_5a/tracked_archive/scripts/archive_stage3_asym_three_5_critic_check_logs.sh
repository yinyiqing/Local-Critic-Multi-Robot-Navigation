#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$PROJECT_ROOT/logs"
DEST_DIR="$PROJECT_ROOT/experiments/多智能体/课程学习/后续计划_集中式Critic核查/01_stage3_asym_three_5_critic对照"
VALID_DIR="$DEST_DIR/logs"
INVALID_DIR="$DEST_DIR/invalid"

mkdir -p "$VALID_DIR" "$INVALID_DIR"

move_if_exists() {
  local src="$1"
  local dest_dir="$2"
  if [[ -f "$SRC_DIR/$src" ]]; then
    mv "$SRC_DIR/$src" "$dest_dir/$src"
    echo "moved: $src -> $dest_dir"
  fi
}

move_if_exists "train_multi_stage3_asym_three_5_joint_action_critic_detached_20260704_223140.log" "$VALID_DIR"
move_if_exists "train_multi_stage3_asym_three_5_context_critic_control_detached_20260704_232939.log" "$VALID_DIR"

move_if_exists "train_multi_stage3_asym_three_5_joint_action_critic_detached_20260704_222937.log" "$INVALID_DIR"
move_if_exists "train_multi_stage3_asym_three_5_joint_action_critic_detached_20260704_223050.log" "$INVALID_DIR"
move_if_exists "train_multi_stage3_asym_three_5_context_critic_control_detached_20260704_230504.log" "$INVALID_DIR"

echo "done"
