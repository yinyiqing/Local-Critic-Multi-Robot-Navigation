# 五车几何邻域 Critic + RewardOnly 测试总结

## 实验口径

- 初始模型：`TD3_velodyne_multi_v4`
- 训练模型：`TD3_velodyne_multi_v4_local_critic_geo_reward_only_5`
- 测试模型：`TD3_velodyne_multi_v4_local_critic_geo_reward_only_5_best`
- 训练日志：`train_multi_local_critic_geo_reward_only_5_detached_20260528_235836.log`
- 原始测试日志：`test_multi_local_critic_geo_reward_only_5_best_detached_20260529_114317.raw.log`
- 清洗测试日志：`test_multi_local_critic_geo_reward_only_5_best_300episodes_clean.log`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 训练选择

训练共运行 20 epochs。best checkpoint 出现在 epoch 9：

| epoch | eval success_rate | eval collision_rate | eval avg_reward | eval avg_env_steps | eval avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 0.900 | 0.080 | 104.608 | 81.2 | 0.317 |

epoch 10 之后评估指标明显退化，因此测试使用 epoch 9 的 best 模型，而不是 latest 模型。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.834 |
| collision_rate | 0.132 |
| unresolved_rate | 0.034 |
| full_success_rate | 0.423 |
| total_success | 1251 / 1500 |
| total_collision | 198 / 1500 |
| total_unresolved | 51 / 1500 |
| total_full_success | 127 / 300 |
| avg_reward | 91.207 |
| avg_env_steps | 101.860 |
| avg_final_distance | 0.462 |

## 与五车主线对比

| 方法 | success_rate | collision_rate | unresolved_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.874 | 0.107 | 0.019 | 0.540 | 103.113 | 62.000 | 0.395 |
| B RewardOnly | 0.881 | 0.080 | 0.039 | 0.533 | 103.216 | 95.277 | 0.407 |
| E 纯几何邻域 Critic | 0.871 | 0.068 | 0.061 | 0.517 | 103.657 | 108.093 | 0.380 |
| F Weighted09 | 0.873 | 0.099 | 0.028 | 0.523 | 102.434 | 71.697 | 0.393 |
| G 几何邻域 Critic + RewardOnly | 0.834 | 0.132 | 0.034 | 0.423 | 91.207 | 101.860 | 0.462 |

## 观察

- G 没有超过 B RewardOnly，且 collision_rate 明显更高。
- G 的 unresolved_rate 不高，说明它不是像 Weighted08 那样主要因为保守和超时变差。
- 几何邻域 critic 与 RewardOnly 组合后，策略更容易碰撞，说明该 critic 信息在五车 RewardOnly 设置下没有带来稳定收益。
- 当前五车标准场景中，B RewardOnly、E 纯几何邻域 Critic、F Weighted09 都比 G 更值得保留为后续比较对象。
