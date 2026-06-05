# Stage 1h Separated Reverse Guard

## Purpose

尝试从 stage1g best 继续训练，针对 `wall_separated_north` 和 `wall_parallel_reverse_clear` 的碰撞尾巴。

## Config

- stage: `stage1h_separated_reverse_guard`
- case file: `../cases/stage1h_separated_reverse_guard_cases.json`
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best`
- best model: `TD3_velodyne_multi_v4_curriculum_stage1h_separated_reverse_guard_from_stage1g_best`
- agents: 1

## Results

- stage1h best epoch: 2
- best eval: `45/48 = 93.75%`, collision `3/48`, no timeout.
- latest regressed to `83.33%` and introduced timeout.

## Interpretation

Stage1h is not used as the main model. Its training direction was unstable. The case set is still useful as a hard evaluation suite for `stage1g` and `stage1i`.

## Logs

- `logs/test/`: stage1g best on this hard suite.
- `logs/superseded/`: stage1h training log, kept for traceability.
