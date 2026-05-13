#!/usr/bin/env bash

# Activate the isolated Python environment for this project only.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DRL_ROBOT_NAV_VENV="/home/jiutian/venvs/drl-robot-nav"

if [ ! -f "$DRL_ROBOT_NAV_VENV/bin/activate" ]; then
  echo "Missing virtual environment: $DRL_ROBOT_NAV_VENV"
  return 1 2>/dev/null || exit 1
fi

source "$DRL_ROBOT_NAV_VENV/bin/activate"

export PYTHONNOUSERSITE=1
export PYTHONPATH="$PROJECT_ROOT/.python_compat${PYTHONPATH:+:$PYTHONPATH}"

echo "Activated DRL robot navigation Python environment."
echo "Python: $(python --version 2>&1)"
echo "Venv: $VIRTUAL_ENV"
