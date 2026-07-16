# Stage 1 Single Local Navigation Curriculum

## Run

- stage: `stage1_single`
- training model: `TD3_velodyne_multi_v4_curriculum_stage1_single`
- warm-start: `TD3_velodyne_multi_v4`
- scenario: `curriculum`
- cases: `../../cases/stage1_single_local_cases.json`
- agents: 1
- max epochs: 8
- eval episodes: 24
- actor lr: 0.0005
- critic lr: 0.0005
- exploration noise: 0.45

## Training Eval

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate | avg_reward | avg_env_steps | avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.125 | 0.042 | 0.833 | 0.125 | 0.833 | -33.995 | 261.9 | 1.606 |
| 2 | 0.792 | 0.042 | 0.167 | 0.792 | 0.167 | 79.959 | 94.8 | 0.730 |
| 3 | 0.792 | 0.042 | 0.167 | 0.792 | 0.167 | 87.671 | 68.7 | 0.659 |
| 4 | 0.875 | 0.000 | 0.125 | 0.875 | 0.125 | 109.957 | 62.7 | 0.341 |
| 5 | 0.667 | 0.042 | 0.292 | 0.667 | 0.292 | 73.086 | 118.8 | 0.701 |
| 6 | 0.708 | 0.000 | 0.292 | 0.708 | 0.292 | 92.783 | 117.1 | 0.370 |
| 7 | 0.250 | 0.042 | 0.708 | 0.250 | 0.708 | 5.894 | 219.2 | 0.700 |
| 8 | 0.292 | 0.000 | 0.708 | 0.292 | 0.708 | 21.810 | 236.6 | 0.724 |

Best checkpoint appears at epoch 4 by `full_success_rate`.

## Best Targeted Test

Tested `TD3_velodyne_multi_v4_curriculum_stage1_single_best` for 24 episodes, cycling the 6 Stage 1 cases 4 times.

| metric | value |
| --- | ---: |
| success_rate | 0.958 |
| collision_rate | 0.000 |
| unresolved_rate | 0.042 |
| full_success_rate | 0.958 |
| timeout_episode_rate | 0.042 |
| avg_env_steps | 49.708 |
| avg_final_distance | 0.277 |

## Comparison To Warm-Start Smoke Test

| model | episodes | success_rate | collision_rate | timeout_episode_rate |
| --- | ---: | ---: | ---: | ---: |
| `TD3_velodyne_multi_v4` | 6 | 0.500 | 0.333 | 0.167 |
| `TD3_velodyne_multi_v4_curriculum_stage1_single_best` | 24 | 0.958 | 0.000 | 0.042 |

## Interpretation

Stage 1 is effective on the targeted local cases. The wall-separated cases that previously caused collision or oscillation are solved in the best targeted test. The remaining failure is one timeout in the near-obstacle recovery case, so the local navigation weakness is not fully eliminated, but it is substantially reduced.

The later training epochs degrade sharply, so Stage 2 should warm-start from `TD3_velodyne_multi_v4_curriculum_stage1_single_best`, not the latest checkpoint.

## Files

原始训练日志、测试 raw log 和 `.npy` 结果已清理；本目录只保留摘要结论和关键指标。
