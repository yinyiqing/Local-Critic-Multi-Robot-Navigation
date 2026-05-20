#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NUM_AGENTS="${DRL_MULTI_RVIZ_NUM_AGENTS:-3}"
ROS_PORT="${DRL_MULTI_RVIZ_ROS_PORT:-11353}"
RVIZ_CONFIG="$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch/pioneer3dx_multi_${NUM_AGENTS}_standard.rviz"

source /opt/ros/noetic/setup.bash
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:${ROS_PORT}
export ROS_PORT_SIM=${ROS_PORT}
export GAZEBO_RESOURCE_PATH="$PROJECT_ROOT/catkin_ws/src/multi_robot_scenario/launch"
cd "$PROJECT_ROOT/catkin_ws"
source devel_isolated/setup.bash

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is empty. Please reconnect with X11 forwarding before launching RViz."
  exit 1
fi

if ! rosnode list >/dev/null 2>&1; then
  echo "ROS master is not reachable at $ROS_MASTER_URI"
  echo "Start the detached multi-agent run first, or set DRL_MULTI_RVIZ_ROS_PORT to the correct port."
  exit 1
fi

python3 "$PROJECT_ROOT/scripts/generate_multi_robot_rviz.py" \
  --num-agents "$NUM_AGENTS" \
  --output "$RVIZ_CONFIG"

rosrun tf static_transform_publisher 0 0 0 0 0 0 map odom 100 >/tmp/rviz_multi_standard_static_tf.log 2>&1 &
static_tf_pid="$!"

overlay_agents="$(seq -s, -f 'r%g' 1 "$NUM_AGENTS")"
python3 "$PROJECT_ROOT/scripts/rviz_multi_agent_overlay.py" \
  --agents "$overlay_agents" \
  --frame odom \
  --tf-style slash \
  >/tmp/rviz_multi_standard_overlay.log 2>&1 &
overlay_pid="$!"

declare -a robot_state_pids=()
for idx in $(seq 1 "$NUM_AGENTS"); do
  name="r${idx}"
  rosparam get "/robot_description_${name}" >"/tmp/${name}_robot_description.xml"
  rosparam set "/${name}/robot_description" --textfile "/tmp/${name}_robot_description.xml"
  ROS_NAMESPACE="/${name}" rosrun robot_state_publisher robot_state_publisher \
    __name:="${name}_robot_state_publisher" \
    _tf_prefix:="${name}" \
    >/tmp/rviz_multi_standard_${name}_rsp.log 2>&1 &
  robot_state_pids+=("$!")
done

cleanup() {
  kill "$static_tf_pid" "$overlay_pid" "${robot_state_pids[@]}" 2>/dev/null || true
}
trap cleanup EXIT

rviz -d "$RVIZ_CONFIG"
