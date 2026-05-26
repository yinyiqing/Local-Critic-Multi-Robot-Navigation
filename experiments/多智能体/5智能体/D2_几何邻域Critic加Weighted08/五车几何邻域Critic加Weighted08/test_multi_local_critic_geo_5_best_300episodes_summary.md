# 五车几何邻域 Critic + Weighted08 测试总结

## 实验口径

- 初始模型：`TD3_velodyne_multi_v4`
- 训练模型：`TD3_velodyne_multi_v4_local_critic_geo_5`
- 测试模型：`TD3_velodyne_multi_v4_local_critic_geo_5_best`
- 训练日志：`train_multi_local_critic_geo_5_detached_20260525_214438.log`
- 原始测试日志：`test_multi_local_critic_geo_5_best_detached_20260526_091118.raw.log`
- 清洗测试日志：`test_multi_local_critic_geo_5_best_300episodes_clean.log`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 方法说明

D2 使用 Weighted08 动态 reward，同时在训练阶段让 critic 额外读取局部邻居几何信息。actor 执行阶段仍只使用本车 observation，不使用邻居信息。

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
| 19 | 0.850 | 0.090 | 102.181 | 113.5 | 0.317 |

epoch 20 的 eval success_rate 回落到 0.720，因此测试使用 epoch 19 的 best 模型，而不是 latest 模型。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.841 |
| collision_rate | 0.082 |
| full_success_rate | 0.420 |
| total_success | 1261 / 1500 |
| total_collision | 123 / 1500 |
| total_full_success | 126 / 300 |
| avg_reward | 98.101 |
| avg_env_steps | 125.343 |
| avg_final_distance | 0.418 |

## 与五车 Baseline 对比

| 方法 | success_rate | collision_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 103.113 | 62.000 | 0.395 |
| D2 几何邻域 Critic + Weighted08 | 0.841 | 0.082 | 0.420 | 98.101 | 125.343 | 0.418 |

## 观察

- D2 的 collision_rate 低于 baseline，说明该策略在五车标准场景中更保守，碰撞有所减少。
- D2 的 success_rate 和 full_success_rate 均低于 baseline，尤其 full_success_rate 从 0.540 降到 0.420。
- D2 的 avg_env_steps 明显更高，说明它完成任务更慢，部分 episode 更容易拖到较长步数。
- 该结果与三车标准场景不同：三车中 D2 优于 baseline，五车中 D2 没有保持整体优势。后续应优先检查五车密集场景，以及邻域阈值、训练稳定性和五车 critic 输入规模是否影响学习。
