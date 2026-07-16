# 五车 Weighted09 测试总结

## 实验口径

- 初始模型：`TD3_velodyne_multi_v4`
- 训练模型：`TD3_velodyne_multi_v4_weighted09_5`
- 测试模型：`TD3_velodyne_multi_v4_weighted09_5_best`
- 训练日志：`train_multi_weighted09_5_detached_20260528_153053.log`
- 原始测试日志：`test_multi_weighted09_5_best_detached_20260528_221626.raw.log`
- 清洗测试日志：`test_multi_weighted09_5_best_300episodes_clean.log`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 训练选择

训练共运行 20 epochs。best checkpoint 出现在 epoch 2：

| epoch | eval success_rate | eval collision_rate | eval avg_reward | eval avg_env_steps | eval avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 0.940 | 0.050 | 119.223 | 49.9 | 0.217 |

epoch 20 的评估指标也较好，但未超过 epoch 2 的 best 选择标准，因此测试使用 epoch 2 的 best 模型。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.873 |
| collision_rate | 0.099 |
| full_success_rate | 0.523 |
| total_success | 1309 / 1500 |
| total_collision | 149 / 1500 |
| total_full_success | 157 / 300 |
| avg_reward | 102.434 |
| avg_env_steps | 71.697 |
| avg_final_distance | 0.393 |

## 与五车主线对比

| 方法 | success_rate | collision_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 103.113 | 62.000 | 0.395 |
| B RewardOnly | 0.881 | 0.080 | 0.533 | 103.216 | 95.277 | 0.407 |
| C Weighted08 | 0.849 | 0.057 | 0.447 | 101.396 | 149.223 | 0.435 |
| D2 几何邻域 Critic + Weighted08 | 0.841 | 0.082 | 0.420 | 98.101 | 125.343 | 0.418 |
| E 纯几何邻域 Critic | 0.871 | 0.068 | 0.517 | 103.657 | 108.093 | 0.380 |
| F Weighted09 | 0.873 | 0.099 | 0.523 | 102.434 | 71.697 | 0.393 |

## 观察

- Weighted09 相比 Weighted08 明显提升 full_success_rate，并把 avg_env_steps 从 149.223 降到 71.697。
- Weighted09 的 collision_rate 比 baseline 略低，但 full_success_rate 仍略低于 baseline。
- 这说明把邻居 reward 权重从 `0.2` 降到 `0.1` 可以缓解保守性，但五车标准场景下还没有带来稳定优势。
- 结合 B/C/F 看，五车场景中动态 reward 的权重需要更谨慎；权重过高会明显削弱个体目标驱动力。
