# Stage 1g Collision Guard

## Purpose

从 stage1f best warm-start，压低墙边平行和 safe/yaw-in case 的 collision。

## Config

- stage: `stage1g_collision_guard`
- case file: `../../cases/stage1g_collision_guard_cases.json`
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage1f_wall_parallel_rescue_from_stage1e_best`
- best model: `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best`
- agents: 1

## Results

- training best epoch: 4
- stage1g targeted test: `120/120`, no collision, no timeout.
- stage1e comprehensive retest with stage1g best: `117/120`, no timeout, 3 collisions.
- stage1h hard-suite retest with stage1g best: `105/120`, 15 collisions, no timeout.

## Interpretation

This is the current baseline single-agent candidate. It solves the main wall-parallel timeout issue, but still has a collision tail in yaw-sensitive separated-wall and reverse wall-parallel cases.

## Logs

- `logs/train/`
- `logs/test/`
- `logs/failed/`
