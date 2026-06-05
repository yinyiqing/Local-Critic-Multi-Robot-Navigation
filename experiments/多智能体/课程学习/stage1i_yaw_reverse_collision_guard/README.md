# Stage 1i Yaw Reverse Collision Guard

## Purpose

从 stage1g best warm-start，更窄地压 `stage1h` hard-suite 中暴露出的 yaw/reverse collision tail。

## Config

- stage: `stage1i_yaw_reverse_collision_guard`
- case file: `../cases/stage1i_yaw_reverse_collision_cases.json`
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best`
- training model: `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g`
- agents: 1
- max epochs: 3
- eval episodes: 72
- actor lr: 0.00002
- critic lr: 0.00002
- exploration noise: 0.025

## Status

Completed run:

- `logs/train/train_multi_curriculum_stage1i_yaw_reverse_collision_guard_detached_20260605_101704.log`

Training eval snapshots:

| epoch | success_rate | collision_rate | unresolved_rate | timeout_episode_rate | note |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 0.958 | 0.042 | 0.000 | 0.000 | best checkpoint created |
| 2 | 0.958 | 0.042 | 0.000 | 0.000 | best checkpoint updated by reward tie-break |
| 3 | 0.681 | 0.167 | 0.153 | 0.153 | latest regressed sharply |

## Checkpoints

- best: `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best`, epoch 2.
- latest: `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_latest`, epoch 4 resume counter after completing 3 epochs.

Do not use latest for comparison. Epoch 3 introduced both collision and timeout regression.

## Decision Rule

Compare only the best checkpoint on:

- `stage1h_separated_reverse_guard` hard suite.
- `stage1e_single_rescue` comprehensive suite.

If it does not beat stage1g best without forgetting solved cases, keep stage1g best as the current single-agent baseline.

## Logs

- `logs/train/`
- `logs/test/`
