# Stage 1f Wall Parallel Rescue

## Purpose

从 stage1e best warm-start，集中补墙边平行通行和 yaw-in 相关失败。

## Config

- stage: `stage1f_wall_parallel_rescue`
- case file: `../../cases/stage1f_wall_parallel_rescue_cases.json`
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage1e_single_rescue_from_stage1_single_best`
- best model: `TD3_velodyne_multi_v4_curriculum_stage1f_wall_parallel_rescue_from_stage1e_best`
- agents: 1

## Results

- training best epoch: 4
- targeted test: `109/120`
- timeout reduced, but wall collision remained.
- `wall_separated_north` reached `10/10`.

## Follow-up

Stage1f solved much of the timeout problem but still left collisions. Continue to `stage1g_collision_guard`.

## Logs

- `logs/train/`
- `logs/test/`
