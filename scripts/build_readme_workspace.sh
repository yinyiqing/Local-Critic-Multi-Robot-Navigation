#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$PROJECT_ROOT/catkin_ws"

source /opt/ros/noetic/setup.bash

export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11311
export ROS_PORT_SIM=11311
export GAZEBO_RESOURCE_PATH="$WORKSPACE_DIR/src/multi_robot_scenario/launch"

cd "$WORKSPACE_DIR"
catkin_make_isolated --cmake-args -DCMAKE_POLICY_VERSION_MINIMUM=3.5

echo
echo "Workspace build completed."
echo "To use it in a shell:"
echo "  source /opt/ros/noetic/setup.bash"
echo "  export ROS_HOSTNAME=localhost"
echo "  export ROS_MASTER_URI=http://localhost:11311"
echo "  export ROS_PORT_SIM=11311"
echo "  export GAZEBO_RESOURCE_PATH=$WORKSPACE_DIR/src/multi_robot_scenario/launch"
echo "  source $WORKSPACE_DIR/devel_isolated/setup.bash"
