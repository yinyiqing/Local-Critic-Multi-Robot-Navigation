#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD3_DIR="$PROJECT_ROOT/TD3"

for dir_name in runs results pytorch_models; do
  if [[ -d "$TD3_DIR/$dir_name" ]]; then
    find "$TD3_DIR/$dir_name" -mindepth 1 -maxdepth 1 ! -name description -exec rm -rf {} +
  fi
done

rm -rf "$TD3_DIR/checkpoints"
rm -f "$PROJECT_ROOT/.train_detached.pid"
rm -f "$PROJECT_ROOT"/logs/train_detached_*.log

echo "Training artifacts removed."
