#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this script with sudo:"
  echo "  sudo bash $0"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y curl gnupg2 lsb-release ca-certificates

if [[ ! -f /etc/apt/sources.list.d/ros1-latest.list ]]; then
  tmp_key="$(mktemp)"
  key_urls=(
    "https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc"
    "https://mirrors.tuna.tsinghua.edu.cn/rosdistro/ros.asc"
  )

  key_ok=0
  for key_url in "${key_urls[@]}"; do
    if curl --connect-timeout 10 --max-time 60 -fL "$key_url" -o "$tmp_key"; then
      key_ok=1
      break
    fi
  done

  if [[ "$key_ok" -ne 1 ]]; then
    echo "Failed to download the ROS archive key from all configured URLs."
    rm -f "$tmp_key"
    exit 1
  fi

  rm -f /usr/share/keyrings/ros-archive-keyring.gpg
  gpg --batch --yes --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg "$tmp_key"
  rm -f "$tmp_key"

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" \
    > /etc/apt/sources.list.d/ros1-latest.list
fi

apt-get update
apt-get install -y \
  ros-noetic-desktop-full \
  python3-rosdep \
  python3-rosinstall \
  python3-rosinstall-generator \
  python3-wstool \
  build-essential

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  rosdep init
fi

echo
echo "ROS Noetic system dependencies are installed."
