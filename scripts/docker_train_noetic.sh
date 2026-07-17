#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${DRL_DOCKER_IMAGE:-local-critic-multi-robot-navigation:noetic}"
CONTAINER_NAME="${DRL_DOCKER_TRAIN_CONTAINER:-drl-noetic-train}"
DOCKER_RUNTIME="${DRL_DOCKER_RUNTIME:-nvidia}"
DOCKER_GPUS="${DRL_DOCKER_GPUS:-all}"
TRAIN_MODE="${DRL_DOCKER_TRAIN_MODE:-single}"
DETACHED="${DRL_DOCKER_DETACHED:-1}"
KEEP_CONTAINER="${DRL_DOCKER_KEEP_CONTAINER:-0}"
ROS_PORT="${DRL_DOCKER_ROS_PORT:-12611}"
GAZEBO_PORT="${DRL_DOCKER_GAZEBO_PORT:-12711}"
DOCKER_USER="${DRL_DOCKER_USER:-$(id -u):$(id -g)}"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"
LOG_BASENAME="docker_train_${TRAIN_MODE}_$(date +%Y%m%d_%H%M%S).log"
HOST_LOG_FILE="$LOG_DIR/$LOG_BASENAME"
CONTAINER_LOG_FILE="/workspace/Local-Critic-Multi-Robot-Navigation/logs/$LOG_BASENAME"
ATTENTION_BASE_MODEL="${DRL_ATTENTION_BASE_MODEL:-TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best}"
ATTENTION_MODEL_NAME="${DRL_ATTENTION_MODEL_NAME:-TD3_velodyne_multi_v9_staged_standard_dense_attention_forward_only}"

if [[ "$TRAIN_MODE" == "attention5d" ]]; then
  base_actor_path="$PROJECT_ROOT/TD3/pytorch_models/${ATTENTION_BASE_MODEL}_actor.pth"
  if [[ ! -f "$base_actor_path" ]]; then
    {
      echo "Missing base Actor initialization: $base_actor_path"
      echo "Restore this file or set DRL_ATTENTION_BASE_MODEL to an existing actor before starting attention5d."
    } | tee "$HOST_LOG_FILE"
    exit 1
  fi
fi

if [[ "${DRL_DOCKER_SKIP_IMAGE_BUILD:-0}" != "1" ]]; then
  "$PROJECT_ROOT/scripts/docker_build_noetic.sh"
fi

extra_env=()
if [[ -n "${DRL_DOCKER_ENV_FILE:-}" ]]; then
  extra_env+=(--env-file "$DRL_DOCKER_ENV_FILE")
fi

run_args=(
  --name "$CONTAINER_NAME"
  --runtime "$DOCKER_RUNTIME"
  --gpus "$DOCKER_GPUS"
  --ipc host
  --pids-limit -1
  --ulimit nproc=65535:65535
  --ulimit nofile=1048576:1048576
  --user "$DOCKER_USER"
  -e HOME=/tmp/drl-home
  -e USER="${USER:-admini}"
  -e LOGNAME="${LOGNAME:-admini}"
  -e DRL_DOCKER_HOST_UID="$(id -u)"
  -e DRL_DOCKER_HOST_GID="$(id -g)"
  -e DRL_ROBOT_NAV_VENV=/opt/drl-robot-nav-venv
  -e PYTHONNOUSERSITE=1
  -e TORCHDYNAMO_DISABLE="${TORCHDYNAMO_DISABLE:-1}"
  -e TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor
  -e CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
  -e NVIDIA_VISIBLE_DEVICES="${NVIDIA_VISIBLE_DEVICES:-all}"
  -e NVIDIA_DRIVER_CAPABILITIES="${NVIDIA_DRIVER_CAPABILITIES:-compute,utility,graphics,display}"
  -e LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-0}"
  -e GAZEBO_HEADLESS_RENDERING=1
  -e DRL_DOCKER_TRAIN_MODE="$TRAIN_MODE"
  -e DRL_DOCKER_ROS_PORT="$ROS_PORT"
  -e DRL_DOCKER_GAZEBO_PORT="$GAZEBO_PORT"
  -e DRL_DOCKER_SKIP_CATKIN_BUILD="${DRL_DOCKER_SKIP_CATKIN_BUILD:-0}"
  -e DRL_ATTENTION_BASE_MODEL="$ATTENTION_BASE_MODEL"
  -e DRL_ATTENTION_MODEL_NAME="$ATTENTION_MODEL_NAME"
  -v "$PROJECT_ROOT":/workspace/Local-Critic-Multi-Robot-Navigation
  -w /workspace/Local-Critic-Multi-Robot-Navigation
)

if [[ "$DETACHED" == "1" ]]; then
  if [[ "$KEEP_CONTAINER" == "1" ]]; then
    run_args=(-d "${run_args[@]}")
  else
    run_args=(-d --rm "${run_args[@]}")
  fi
else
  if [[ "$KEEP_CONTAINER" == "1" ]]; then
    run_args=("${run_args[@]}")
  else
    run_args=(--rm "${run_args[@]}")
  fi
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

container_id="$(
  docker run "${run_args[@]}" "${extra_env[@]}" "$IMAGE_NAME" bash -lc "
    set -eo pipefail
    cleanup_permissions() {
      if [[ \"\$(id -u)\" == \"0\" ]]; then
        chown -R \"\${DRL_DOCKER_HOST_UID}:\${DRL_DOCKER_HOST_GID}\" \
          logs TD3/checkpoints TD3/pytorch_models TD3/runs TD3/results TD3/assets \
          >/dev/null 2>&1 || true
      fi
    }
    trap cleanup_permissions EXIT
    mkdir -p \"\$HOME\"
    source /opt/ros/noetic/setup.bash
    export ROS_HOSTNAME=localhost
    export ROS_MASTER_URI=http://localhost:${ROS_PORT}
    export ROS_PORT_SIM=${ROS_PORT}
    export GAZEBO_MASTER_URI=http://localhost:${GAZEBO_PORT}
    export GAZEBO_RESOURCE_PATH=/workspace/Local-Critic-Multi-Robot-Navigation/catkin_ws/src/multi_robot_scenario/launch
    if [[ \"\${DRL_DOCKER_SKIP_CATKIN_BUILD:-0}\" != \"1\" ]]; then
      cd catkin_ws
      catkin_make_isolated --cmake-args -DCMAKE_POLICY_VERSION_MINIMUM=3.5
      cd ..
    fi
    source catkin_ws/devel_isolated/setup.bash
    source ./env.python.sh
    case \"$TRAIN_MODE\" in
      single)
        export DRL_TRAIN_LAUNCHFILE=\"\${DRL_TRAIN_LAUNCHFILE:-multi_robot_scenario_headless.launch}\"
        cd TD3
        python3 -u train_velodyne_td3.py > '$CONTAINER_LOG_FILE' 2>&1
        ;;
      multi)
        export DRL_MULTI_TRAIN_LAUNCHFILE=\"\${DRL_MULTI_TRAIN_LAUNCHFILE:-multi_robot_scenario_multi_2.launch}\"
        cd TD3
        python3 -u train_velodyne_td3_multi.py > '$CONTAINER_LOG_FILE' 2>&1
        ;;
      attention5d)
        LAUNCHFILE=\"\${DRL_ATTENTION_LAUNCHFILE:-multi_robot_scenario_attention_5.launch}\"
        CASES_PATH=\"\${DRL_MULTI_CURRICULUM_CASES:-/workspace/Local-Critic-Multi-Robot-Navigation/experiments/cases/attention_mixed_5.json}\"
        BASE_MODEL=\"\${DRL_ATTENTION_BASE_MODEL:-TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best}\"
        if [[ ! -f \"TD3/pytorch_models/\${BASE_MODEL}_actor.pth\" ]]; then
          echo \"Missing base Actor initialization: TD3/pytorch_models/\${BASE_MODEL}_actor.pth\" | tee '$CONTAINER_LOG_FILE'
          exit 1
        fi
        python3 scripts/generate_multi_robot_launch.py --num-agents 5 --output \"TD3/assets/\$LAUNCHFILE\"
        export DRL_MULTI_CURRICULUM_CASES=\"\$CASES_PATH\"
        export DRL_MULTI_CURRICULUM_SAMPLING=\"\${DRL_MULTI_CURRICULUM_SAMPLING:-random}\"
        export DRL_ATTENTION_LAUNCHFILE=\"\$LAUNCHFILE\"
        export DRL_ATTENTION_BASE_MODEL=\"\$BASE_MODEL\"
        cd TD3
        python3 -u train_spatiotemporal_attention.py > '$CONTAINER_LOG_FILE' 2>&1
        ;;
      *)
        echo \"Unknown DRL_DOCKER_TRAIN_MODE: $TRAIN_MODE\" | tee '$CONTAINER_LOG_FILE'
        exit 2
        ;;
    esac
  "
)"

if [[ "$DETACHED" == "1" ]]; then
  echo "Docker training started."
  echo "Container: $CONTAINER_NAME ($container_id)"
  echo "Mode: $TRAIN_MODE"
  echo "GPU: $DOCKER_GPUS"
  echo "ROS/Gazebo ports: $ROS_PORT / $GAZEBO_PORT"
  echo "Log: $HOST_LOG_FILE"
else
  echo "Docker training finished."
  echo "Log: $HOST_LOG_FILE"
fi
