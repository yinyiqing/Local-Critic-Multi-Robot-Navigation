# 五车 RewardOnly 测试总结

## 实验口径

- 初始模型：`TD3_velodyne_multi_v4`
- 训练模型：`TD3_velodyne_multi_v4_reward_only_5`
- 测试模型：`TD3_velodyne_multi_v4_reward_only_5_best`
- 训练日志：`train_multi_reward_only_5_detached_20260526_230021.log`
- 原始测试日志：`test_multi_reward_only_5_best_detached_20260527_084356.raw.log`
- 清洗测试日志：`test_multi_reward_only_5_best_300episodes_clean.log`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 训练选择

训练共运行 20 epochs。best checkpoint 出现在 epoch 5：

| epoch | eval success_rate | eval collision_rate | eval avg_reward | eval avg_env_steps | eval avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 0.890 | 0.080 | 105.050 | 84.2 | 0.321 |

epoch 5 后评估指标明显退化，因此测试使用 epoch 5 的 best 模型，而不是 latest 模型。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.881 |
| collision_rate | 0.080 |
| full_success_rate | 0.533 |
| total_success | 1321 / 1500 |
| total_collision | 120 / 1500 |
| total_full_success | 160 / 300 |
| avg_reward | 103.216 |
| avg_env_steps | 95.277 |
| avg_final_distance | 0.407 |

## 与五车 Baseline 和 D2 对比

| 方法 | success_rate | collision_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 103.113 | 62.000 | 0.395 |
| B RewardOnly | 0.881 | 0.080 | 0.533 | 103.216 | 95.277 | 0.407 |
| D2 几何邻域 Critic + Weighted08 | 0.841 | 0.082 | 0.420 | 98.101 | 125.343 | 0.418 |

## 观察

- RewardOnly 的 success_rate 略高于 baseline，collision_rate 低于 baseline。
- RewardOnly 的 full_success_rate 略低于 baseline，avg_env_steps 更高，说明策略完成更慢。
- 相比 D2，RewardOnly 的 full_success_rate 明显更高，说明五车 D2 的下降不太可能只由动态 reward 引起，critic 结构或 Weighted08 组合仍需继续检查。
