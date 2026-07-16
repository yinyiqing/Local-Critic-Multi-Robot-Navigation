#!/usr/bin/env bash
set -eo pipefail

CONTAINER_NAME="${1:-${DRL_DOCKER_TRAIN_CONTAINER:-drl-noetic-train}}"
GRACE_SECONDS="${DRL_DOCKER_STOP_GRACE_SECONDS:-60}"

if ! docker ps --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  echo "No running Docker training container named: $CONTAINER_NAME"
  exit 0
fi

docker kill --signal=SIGINT "$CONTAINER_NAME" >/dev/null
for _ in $(seq 1 "$GRACE_SECONDS"); do
  if ! docker ps --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
    echo "Stopped Docker training container: $CONTAINER_NAME"
    exit 0
  fi
  sleep 1
done

docker stop --time 15 "$CONTAINER_NAME" >/dev/null
echo "Stopped Docker training container after timeout: $CONTAINER_NAME"
