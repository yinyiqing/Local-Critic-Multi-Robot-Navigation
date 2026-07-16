#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${DRL_DOCKER_IMAGE:-local-critic-multi-robot-navigation:noetic}"
DOCKER_RUNTIME="${DRL_DOCKER_RUNTIME:-nvidia}"
DOCKER_GPUS="${DRL_DOCKER_GPUS:-all}"

docker run --rm -it \
  --runtime "$DOCKER_RUNTIME" \
  --gpus "$DOCKER_GPUS" \
  --network host \
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
  bash -lc 'mkdir -p "$HOME"; exec bash'
