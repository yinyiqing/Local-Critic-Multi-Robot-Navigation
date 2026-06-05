# Stage 2 Dense Five-Agent Run Stopped As Too Hard

## Run

- stage: `stage2_dense`
- model: `TD3_velodyne_multi_v4_curriculum_stage2_dense_5`
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage1_single_best`
- agents: 5
- cases: `../../../cases/stage2_dense_multi_cases.json`
- started: `20260602_141432`
- stopped manually after epoch 1 and early epoch 2

## Observed Signal

Epoch 1 eval:

| metric | value |
| --- | ---: |
| success_rate | 0.075 |
| collision_rate | 0.517 |
| unresolved_rate | 0.408 |
| full_success_rate | 0.000 |
| timeout_episode_rate | 0.917 |
| avg_env_steps | 285.9 |

Early training episodes continued to show frequent `3/5` to `5/5` collisions. This indicates that jumping directly from Stage 1 single-agent local navigation to five-agent dense interaction is too steep.

## Decision

Stop this run and insert an intermediate `stage2_three_dense` course with 3 agents. The five-agent dense course should be revisited after the 3-agent dense course has produced a stable best checkpoint.

## Files

原始训练日志已清理；本目录只保留中止原因和关键指标摘要。
