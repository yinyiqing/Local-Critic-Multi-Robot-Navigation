#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$PROJECT_ROOT/catkin_ws"

# Clean up stale processes from previous runs of this project only.
for pattern in \
  "/opt/ros/noetic/bin/roscore -p 11311" \
  "/opt/ros/noetic/bin/rosmaster --core -p 11311" \
  "/opt/ros/noetic/bin/roslaunch -p 11311 $PROJECT_ROOT/TD3/assets/multi_robot_scenario.launch" \
  "/opt/ros/noetic/lib/gazebo_ros/gzserver -e ode TD3.world" \
  "gzserver -e ode TD3.world -s /opt/ros/noetic/lib/libgazebo_ros_paths_plugin.so -s /opt/ros/noetic/lib/libgazebo_ros_api_plugin.so"
do
  pkill -f "$pattern" 2>/dev/null || true
done

sleep 2

source /opt/ros/noetic/setup.bash
source "$PROJECT_ROOT/env.python.sh"

export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11311
export ROS_PORT_SIM=11311
export GAZEBO_RESOURCE_PATH="$WORKSPACE_DIR/src/multi_robot_scenario/launch"

cd "$WORKSPACE_DIR"
source devel_isolated/setup.bash

cd "$PROJECT_ROOT/TD3"
python3 train_velodyne_td3.py
