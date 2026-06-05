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

## Hard-Suite Retest

Model: `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best`

Test suite: `stage1h_separated_reverse_guard`, 120 episodes.

| metric | value |
| --- | ---: |
| total_success | 112 / 120 |
| total_collision | 8 / 120 |
| total_unresolved | 0 / 120 |
| timeout_episodes | 0 / 120 |
| success_rate | 0.933 |
| collision_rate | 0.067 |

Compared with stage1g best on the same suite (`105/120`, 15 collisions), stage1i best improves the hard-suite result by 7 successes and removes no-timeout regressions. The remaining failures are still collision tails, mainly:

| case | success | collision |
| --- | ---: | ---: |
| `wall_parallel_reverse_safe` | 8 / 10 | 2 / 10 |
| `wall_separated_north` | 8 / 10 | 2 / 10 |
| `wall_parallel_north_clear_straight` | 9 / 10 | 1 / 10 |
| `wall_parallel_reverse_clear` | 9 / 10 | 1 / 10 |
| `wall_separated_north_yaw_in` | 9 / 10 | 1 / 10 |
| `wall_separated_north_yaw_out` | 9 / 10 | 1 / 10 |

Next check is the `stage1e_single_rescue` comprehensive suite. Stage1i best should only replace stage1g best if it keeps the broad single-agent result near or above stage1g's `117/120`.

## Comprehensive Retest

Test suite: `stage1e_single_rescue`, 120 episodes.

| metric | value |
| --- | ---: |
| total_success | 115 / 120 |
| total_collision | 5 / 120 |
| total_unresolved | 0 / 120 |
| timeout_episodes | 0 / 120 |
| success_rate | 0.958 |
| collision_rate | 0.042 |

Compared with stage1g best on the same suite (`117/120`, 3 collisions), stage1i best gives up 2 successes on the broader suite while improving the hard suite by 7 successes. It is therefore a candidate when the priority is hard-suite collision reduction, but not an unconditional replacement for stage1g best.

Remaining comprehensive failures:

| case | success | collision |
| --- | ---: | ---: |
| `wall_parallel_north_safe_straight` | 8 / 10 | 2 / 10 |
| `wall_separated_north` | 8 / 10 | 2 / 10 |
| `wall_parallel_north_clear_yaw_out` | 9 / 10 | 1 / 10 |

## Logs

- `logs/train/`
- `logs/test/`
