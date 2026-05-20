#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source /opt/ros/noetic/setup.bash
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11352
export ROS_PORT_SIM=11352
export GAZEBO_RESOURCE_PATH="$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch"
cd "$PROJECT_ROOT/catkin_ws"
source devel_isolated/setup.bash

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is empty. Please reconnect with X11 forwarding before launching RViz."
  exit 1
fi

if ! rosnode list >/dev/null 2>&1; then
  echo "ROS master is not reachable at $ROS_MASTER_URI"
  echo "Start detached 3-agent local-critic training first, or confirm it is still running."
  exit 1
fi

rosrun tf static_transform_publisher 0 0 0 0 0 0 map odom 100 >/tmp/rviz_multi_local_critic_3_static_tf.log 2>&1 &
static_tf_pid="$!"

python3 "$PROJECT_ROOT/scripts/rviz_multi_agent_overlay.py" \
  --agents r1,r2,r3 \
  --frame odom \
  >/tmp/rviz_multi_local_critic_3_overlay.log 2>&1 &
overlay_pid="$!"
trap 'kill "$static_tf_pid" "$overlay_pid" 2>/dev/null || true' EXIT

rviz -d "$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch/pioneer3dx_multi_3.rviz"
