#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${DRL_DOCKER_IMAGE:-local-critic-multi-robot-navigation:noetic}"
CONTAINER_NAME="${DRL_DOCKER_SMOKE_CONTAINER:-drl-noetic-smoke}"
ROS_PORT="${DRL_DOCKER_ROS_PORT:-12411}"
GAZEBO_PORT="${DRL_DOCKER_GAZEBO_PORT:-12511}"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"
LOG_BASENAME="docker_smoke_$(date +%Y%m%d_%H%M%S).log"
HOST_LOG_FILE="$LOG_DIR/$LOG_BASENAME"
CONTAINER_LOG_FILE="/workspace/Local-Critic-Multi-Robot-Navigation/logs/$LOG_BASENAME"

if [[ "${DRL_DOCKER_SKIP_IMAGE_BUILD:-0}" != "1" ]]; then
  "$PROJECT_ROOT/scripts/docker_build_noetic.sh"
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker run -d --rm \
  --name "$CONTAINER_NAME" \
  --runtime "${DRL_DOCKER_RUNTIME:-nvidia}" \
  --gpus "${DRL_DOCKER_GPUS:-all}" \
  --ipc host \
  --pids-limit -1 \
  --ulimit nproc=65535:65535 \
  --ulimit nofile=1048576:1048576 \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/drl-home \
  -e USER="${USER:-admini}" \
  -e LOGNAME="${LOGNAME:-admini}" \
  -e DRL_ROBOT_NAV_VENV=/opt/drl-robot-nav-venv \
  -e PYTHONNOUSERSITE=1 \
  -e TORCHDYNAMO_DISABLE="${TORCHDYNAMO_DISABLE:-1}" \
  -e TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor \
  -e CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" \
  -e NVIDIA_VISIBLE_DEVICES="${NVIDIA_VISIBLE_DEVICES:-all}" \
  -e NVIDIA_DRIVER_CAPABILITIES="${NVIDIA_DRIVER_CAPABILITIES:-compute,utility,graphics,display}" \
  -e LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-0}" \
  -e GAZEBO_HEADLESS_RENDERING=1 \
  -v "$PROJECT_ROOT":/workspace/Local-Critic-Multi-Robot-Navigation \
  -w /workspace/Local-Critic-Multi-Robot-Navigation \
  "$IMAGE_NAME" \
  bash -lc "
    set -eo pipefail
    mkdir -p \"\$HOME\"
    source /opt/ros/noetic/setup.bash
    export ROS_HOSTNAME=localhost
    export ROS_MASTER_URI=http://localhost:${ROS_PORT}
    export ROS_PORT_SIM=${ROS_PORT}
    export GAZEBO_MASTER_URI=http://localhost:${GAZEBO_PORT}
    export GAZEBO_RESOURCE_PATH=/workspace/Local-Critic-Multi-Robot-Navigation/catkin_ws/src/multi_robot_scenario/launch
    cd catkin_ws
    catkin_make_isolated --cmake-args -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    cd ..
    source catkin_ws/devel_isolated/setup.bash
    source ./env.python.sh
    cd TD3
    DRL_MAX_EPISODES=1 DRL_MAX_TIMESTEPS=5 python3 -u train_velodyne_td3.py > '$CONTAINER_LOG_FILE' 2>&1
  "

echo "Docker smoke started."
echo "Container: $CONTAINER_NAME"
echo "ROS/Gazebo ports: $ROS_PORT / $GAZEBO_PORT"
echo "Log: $HOST_LOG_FILE"
