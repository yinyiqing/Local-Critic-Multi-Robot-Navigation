# Stage 2a 三车密集中间课程诊断

## 口径

- 训练模型：`TD3_velodyne_multi_v4_curriculum_stage2_three_dense_3`
- warm-start：`TD3_velodyne_multi_v4_curriculum_stage1_single_best`
- case 文件：`../../cases/stage2_three_dense_cases.json`
- 机器人数量：3
- 原始运行产物：已清理，仅保留复盘摘要

## 训练结果

第一段训练跑到 epoch 8，epoch 8 更新 best。

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate | avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 0.625 | 0.306 | 0.069 | 0.375 | 0.208 | 0.803 |
| 7 | 0.708 | 0.222 | 0.069 | 0.250 | 0.208 | 0.616 |
| 8 | 0.750 | 0.194 | 0.056 | 0.583 | 0.167 | 0.534 |

续训到 epoch 10 后指标回落。

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate | avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 0.694 | 0.236 | 0.069 | 0.417 | 0.208 | 0.535 |
| 10 | 0.611 | 0.194 | 0.194 | 0.208 | 0.458 | 0.708 |

## 观察

- epoch 8 是当前 best，但继续训练没有稳定改善。
- RViz 中近目标聚集、侧墙附近和目标很近的场景频繁出现左右摆动。
- 三车 dense case 暴露的主要问题不是协同策略已经成型后的小幅优化，而是底层局部导航在近目标和墙面干扰下仍不稳。

## 判断

Stage 2a 暂停继续训练。下一步应先补 Stage 1b，集中复现近目标捕获和侧墙振荡，再考虑回到三车密集中间课程。
