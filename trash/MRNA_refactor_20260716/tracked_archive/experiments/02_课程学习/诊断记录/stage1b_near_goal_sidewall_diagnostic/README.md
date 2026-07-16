# Stage 1b 近目标和侧墙诊断测试

## 口径

- 测试模型：`TD3_velodyne_multi_v4_curriculum_stage1_single_best`
- case 文件：`../../cases/stage1b_single_near_goal_sidewall_cases.json`
- 机器人数量：1
- 测试集数：64 episodes，8 个 case 循环 8 遍
- 原始运行产物：已清理，仅保留复盘摘要

## 总体结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.906 |
| collision_rate | 0.016 |
| unresolved_rate | 0.078 |
| timeout_episode_rate | 0.078 |
| total_success | 58 / 64 |
| total_collision | 1 / 64 |
| total_unresolved | 5 / 64 |

## 按 case 统计

| case | episodes | success | collision | unresolved | timeout | avg_steps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| near_goal_tangent_left | 8 | 8 | 0 | 0 | 0 | 4.5 |
| near_goal_tangent_right | 8 | 8 | 0 | 0 | 0 | 7.6 |
| near_goal_overshoot_return | 8 | 8 | 0 | 0 | 0 | 23.4 |
| side_wall_goal_south | 8 | 8 | 0 | 0 | 0 | 43.6 |
| side_wall_goal_north | 8 | 8 | 0 | 0 | 0 | 34.2 |
| wall_parallel_close_pass | 8 | 4 | 1 | 3 | 3 | 224.1 |
| goal_adjacent_wall_capture | 8 | 6 | 0 | 2 | 2 | 91.5 |
| close_goal_reversal | 8 | 8 | 0 | 0 | 0 | 16.8 |

## 判断

Stage 1 best 在简单近目标捕获上表现稳定，但在墙面约束更强的 case 上仍然不稳。

两个主要失败点：

- `wall_parallel_close_pass`：侧墙平行通过时高频超时，并出现 1 次碰撞。
- `goal_adjacent_wall_capture`：目标贴近墙面时出现超时，说明近目标捕获和避障之间仍会拉扯。

因此 Stage 1b 不需要从零重来，应从 Stage 1 best warm-start，集中补训这两个失败 case，并保留少量已通过 case 防止遗忘。
