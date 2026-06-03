# Stage 1b hard-only 训练诊断

## 口径

- 初始模型：`TD3_velodyne_multi_v4_curriculum_stage1b_single_best`
- hard-only 训练模型：`TD3_velodyne_multi_v4_curriculum_stage1b_hard_only`
- case 文件：`../cases/stage1b_hard_only_cases.json`
- hard-only case：
  - `wall_parallel_close_pass`
  - `goal_adjacent_wall_capture`
- 机器人数量：1
- 主要日志：
  - `train_multi_curriculum_stage1b_single_detached_20260602_215749.log`
  - `train_multi_curriculum_stage1b_hard_only_detached_20260602_231108.log`
  - `test_multi_curriculum_stage1b_hard_only_TD3_velodyne_multi_v4_curriculum_stage1b_hard_only_best_detached_20260603_090928.log`

## Stage 1b uniform 训练

从 Stage 1 best 继续训练完整 Stage 1b case。第 3 个 epoch 恢复到 targeted test 的水平，但没有明显超过原始模型。

| epoch | success_rate | collision_rate | unresolved_rate | timeout_episode_rate |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.844 | 0.031 | 0.125 | 0.125 |
| 2 | 0.875 | 0.000 | 0.125 | 0.125 |
| 3 | 0.906 | 0.000 | 0.094 | 0.094 |

## hard-only 训练

只保留两个最难 case 后，超时和 unresolved 明显下降，但碰撞升高。

| epoch | success_rate | collision_rate | unresolved_rate | timeout_episode_rate | avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.531 | 0.125 | 0.344 | 0.344 | 1.121 |
| 2 | 0.562 | 0.062 | 0.375 | 0.375 | 0.990 |
| 3 | 0.688 | 0.062 | 0.250 | 0.250 | 0.856 |
| 4 | 0.625 | 0.062 | 0.312 | 0.312 | 0.946 |
| 5 | 0.688 | 0.219 | 0.094 | 0.094 | 0.627 |
| 6 | 0.781 | 0.188 | 0.031 | 0.031 | 0.548 |

## hard-only best 确定性测试

测试 `TD3_velodyne_multi_v4_curriculum_stage1b_hard_only_best`，64 episodes，两个 hard case 循环采样。

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.797 |
| collision_rate | 0.156 |
| unresolved_rate | 0.047 |
| timeout_episode_rate | 0.047 |
| total_success | 51 / 64 |
| total_collision | 10 / 64 |
| total_unresolved | 3 / 64 |

按 case 粗分：

| case | episodes | success | collision | unresolved |
| --- | ---: | ---: | ---: | ---: |
| wall_parallel_close_pass | 32 | 20 | 10 | 2 |
| goal_adjacent_wall_capture | 32 | 31 | 0 | 1 |

## 判断

hard-only 训练确实解决了 `goal_adjacent_wall_capture`，但没有可靠解决 `wall_parallel_close_pass`。它把一部分“超时/摆动”转成了“快速碰撞”，因此暂不适合作为后续多车课程的 warm-start 主线。

当前更稳的单车补课基准仍是 `TD3_velodyne_multi_v4_curriculum_stage1b_single_best`。后续如果继续补 Stage 1b，应围绕 `wall_parallel_close_pass` 单独做更细的安全边界或速度控制诊断，而不是直接继续 hard-only 训练。
