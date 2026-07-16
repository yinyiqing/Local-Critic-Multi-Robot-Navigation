# 五车 Weighted08 测试总结

## 实验口径

- 初始模型：`TD3_velodyne_multi_v4`
- 训练模型：`TD3_velodyne_multi_v4_weighted08_5`
- 测试模型：`TD3_velodyne_multi_v4_weighted08_5_best`
- 训练日志：`train_multi_weighted08_5_detached_20260527_103842.log`
- 原始测试日志：`test_multi_weighted08_5_best_detached_20260527_164757.raw.log`
- 清洗测试日志：`test_multi_weighted08_5_best_300episodes_clean.log`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 训练选择

训练共运行 20 epochs。best checkpoint 出现在 epoch 18：

| epoch | eval success_rate | eval collision_rate | eval avg_reward | eval avg_env_steps | eval avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 18 | 0.930 | 0.030 | 117.371 | 89.2 | 0.261 |

epoch 19 和 epoch 20 的评估指标明显回落，因此测试使用 epoch 18 的 best 模型，而不是 latest 模型。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.849 |
| collision_rate | 0.057 |
| full_success_rate | 0.447 |
| total_success | 1273 / 1500 |
| total_collision | 86 / 1500 |
| total_full_success | 134 / 300 |
| avg_reward | 101.396 |
| avg_env_steps | 149.223 |
| avg_final_distance | 0.435 |

## 与五车主线对比

| 方法 | success_rate | collision_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 103.113 | 62.000 | 0.395 |
| B RewardOnly | 0.881 | 0.080 | 0.533 | 103.216 | 95.277 | 0.407 |
| C Weighted08 | 0.849 | 0.057 | 0.447 | 101.396 | 149.223 | 0.435 |
| D2 几何邻域 Critic + Weighted08 | 0.841 | 0.082 | 0.420 | 98.101 | 125.343 | 0.418 |

## 观察

- Weighted08 的 collision_rate 明显低于 baseline，说明距离加权邻居 reward 会让策略更保守。
- Weighted08 的 success_rate 和 full_success_rate 低于 baseline，avg_env_steps 明显更高，说明它牺牲了完成效率。
- 相比 RewardOnly，Weighted08 的 full_success_rate 下降明显，说明五车场景中 `0.8 own + 0.2 neighbor` 的加权形式可能比简单 RewardOnly 更容易削弱个体目标驱动力。
- D2 比 Weighted08 略低，说明几何邻域 critic 没有弥补 Weighted08 的问题，反而继续保持了偏保守趋势。
