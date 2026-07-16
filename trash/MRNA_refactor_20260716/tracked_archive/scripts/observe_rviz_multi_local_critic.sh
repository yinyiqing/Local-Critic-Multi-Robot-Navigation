#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source /opt/ros/noetic/setup.bash
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11351
export ROS_PORT_SIM=11351
export GAZEBO_RESOURCE_PATH="$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch"
cd "$PROJECT_ROOT/catkin_ws"
source devel_isolated/setup.bash

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is empty. Please reconnect with X11 forwarding before launching RViz."
  exit 1
fi

if ! rosnode list >/dev/null 2>&1; then
  echo "ROS master is not reachable at $ROS_MASTER_URI"
  echo "Start detached local-critic multi-agent training first, or confirm it is still running."
  exit 1
fi

rviz -d "$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch/pioneer3dx_multi.rviz"
