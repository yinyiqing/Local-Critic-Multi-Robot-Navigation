#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${DRL_DOCKER_IMAGE:-local-critic-multi-robot-navigation:noetic}"
PIP_INDEX_URL="${DRL_PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PYTHON_VERSION="${DRL_PYTHON_VERSION:-3.10}"
PYTORCH_INDEX_URL="${DRL_PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu128}"
TORCH_PACKAGE="${DRL_TORCH_PACKAGE:-torch}"

cd "$PROJECT_ROOT"
docker build \
  --build-arg "PIP_INDEX_URL=$PIP_INDEX_URL" \
  --build-arg "PYTHON_VERSION=$PYTHON_VERSION" \
  --build-arg "PYTORCH_INDEX_URL=$PYTORCH_INDEX_URL" \
  --build-arg "TORCH_PACKAGE=$TORCH_PACKAGE" \
  -f Dockerfile.noetic \
  -t "$IMAGE_NAME" \
  .
