# Stage 1e Single Rescue

## Purpose

从 `stage1_single_best` warm-start，补近目标捕获、目标贴墙和可行墙边行驶。这个阶段确认单车基础缺陷仍未完全解决。

## Config

- stage: `stage1e_single_rescue`
- case file: `../cases/stage1e_single_rescue_cases.json`
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage1_single_best`
- best model: `TD3_velodyne_multi_v4_curriculum_stage1e_single_rescue_from_stage1_single_best`
- agents: 1

## Results

- training best epoch: 8
- stage1e targeted test with stage1e best: `103/120`
- remaining weak cases included `wall_parallel_north_safe_straight`, yaw variants, and `wall_separated_north`.

## Follow-up

Stage1e improved near-goal behavior but did not solve wall-parallel and separated-wall cases. Continue to `stage1f_wall_parallel_rescue`.

## Logs

- `logs/train/`
- `logs/test/`
- `logs/failed/`
