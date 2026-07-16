#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${DRL_DOCKER_IMAGE:-local-critic-multi-robot-navigation:noetic}"
CONTAINER_NAME="${DRL_DOCKER_GPU_CHECK_CONTAINER:-drl-noetic-gpu-check}"

if [[ "${DRL_DOCKER_SKIP_IMAGE_BUILD:-0}" != "1" ]]; then
  "$PROJECT_ROOT/scripts/docker_build_noetic.sh"
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker run --rm \
  --name "$CONTAINER_NAME" \
  --runtime "${DRL_DOCKER_RUNTIME:-nvidia}" \
  --gpus "${DRL_DOCKER_GPUS:-all}" \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/drl-home \
  -e DRL_ROBOT_NAV_VENV=/opt/drl-robot-nav-venv \
  -e PYTHONNOUSERSITE=1 \
  -e TORCHDYNAMO_DISABLE="${TORCHDYNAMO_DISABLE:-1}" \
  -e TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor \
  -v "$PROJECT_ROOT":/workspace/Local-Critic-Multi-Robot-Navigation \
  -w /workspace/Local-Critic-Multi-Robot-Navigation \
  "$IMAGE_NAME" \
  bash -lc '
    set -eo pipefail
    mkdir -p "$HOME"
    nvidia-smi
    source ./env.python.sh
    python3 - <<'"'"'PY'"'"'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("device", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")
PY
  '
