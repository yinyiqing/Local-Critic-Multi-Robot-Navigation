# 五车纯几何邻域 Critic 测试总结

## 实验口径

- 初始模型：`TD3_velodyne_multi_v4`
- 训练模型：`TD3_velodyne_multi_v4_local_critic_geo_individual_5`
- 测试模型：`TD3_velodyne_multi_v4_local_critic_geo_individual_5_best`
- 训练日志：`train_multi_local_critic_geo_individual_5_detached_20260527_203955.log`
- 原始测试日志：`test_multi_local_critic_geo_individual_5_best_detached_20260528_092253.raw.log`
- 清洗测试日志：`test_multi_local_critic_geo_individual_5_best_300episodes_clean.log`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 方法说明

该实验只引入几何邻域 critic，不引入 RewardOnly 或 Weighted08。训练阶段 critic 可以读取局部邻居几何信息；执行阶段 actor 仍只使用本车 observation。

每个邻居 context 包含：

| 字段 | 含义 |
| --- | --- |
| `relative_x` | 邻居相对本车的 x 方向位置 |
| `relative_y` | 邻居相对本车的 y 方向位置 |
| `distance` | 邻居与本车的距离 |
| `bearing` | 邻居相对本车朝向的方位角 |
| `mask` | 该邻居槽位是否有效 |

## 训练选择

训练共运行 20 epochs。best checkpoint 出现在 epoch 19：

| epoch | eval success_rate | eval collision_rate | eval avg_reward | eval avg_env_steps | eval avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 19 | 0.920 | 0.040 | 113.772 | 98.3 | 0.257 |

epoch 20 的 eval success_rate 回落到 0.860，因此测试使用 epoch 19 的 best 模型，而不是 latest 模型。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.871 |
| collision_rate | 0.068 |
| full_success_rate | 0.517 |
| total_success | 1307 / 1500 |
| total_collision | 102 / 1500 |
| total_full_success | 155 / 300 |
| avg_reward | 103.657 |
| avg_env_steps | 108.093 |
| avg_final_distance | 0.380 |

## 与五车主线对比

| 方法 | success_rate | collision_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 103.113 | 62.000 | 0.395 |
| B RewardOnly | 0.881 | 0.080 | 0.533 | 103.216 | 95.277 | 0.407 |
| C Weighted08 | 0.849 | 0.057 | 0.447 | 101.396 | 149.223 | 0.435 |
| D2 几何邻域 Critic + Weighted08 | 0.841 | 0.082 | 0.420 | 98.101 | 125.343 | 0.418 |
| E 纯几何邻域 Critic | 0.871 | 0.068 | 0.517 | 103.657 | 108.093 | 0.380 |

## 观察

- 纯几何邻域 Critic 的 success_rate 与 baseline 接近，collision_rate 低于 baseline，但 full_success_rate 略低。
- 相比 C Weighted08 和 D2，E 的 full_success_rate 明显更高，说明几何邻域 critic 单独并不会造成 D2 那样明显的下降。
- E 的 avg_env_steps 高于 baseline，说明它仍然比 baseline 更保守一些。
- 综合看，五车 D2 的下降主要来自 Weighted08 造成的目标驱动力削弱；几何邻域 critic 本身较稳定，但没有在五车标准场景中带来超过 baseline 的整体收益。
