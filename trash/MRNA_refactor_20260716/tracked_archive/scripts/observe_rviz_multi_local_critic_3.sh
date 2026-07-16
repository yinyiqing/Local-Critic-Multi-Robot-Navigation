#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DRL_MULTI_RVIZ_NUM_AGENTS=3
export DRL_MULTI_RVIZ_ROS_PORT=11352
exec "$PROJECT_ROOT/scripts/observe_rviz_multi_standard.sh"
