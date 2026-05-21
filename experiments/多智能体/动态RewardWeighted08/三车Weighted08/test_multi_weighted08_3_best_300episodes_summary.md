# 三车 Weighted08 best checkpoint 测试摘要

## 测试对象

- 模型：`TD3_velodyne_multi_v4_weighted08_3_best`
- 场景：三车，`r1, r2, r3`
- 测试规模：300 episodes
- 测试阶段 reward：individual reward，仅用于统计策略表现
- Actor 输入：本车 24 维 observation
- Critic 输入：本车 24 维 observation，不使用局部邻域 context
- 训练 reward：`0.8 * own reward + 0.2 * distance-weighted visible-neighbor reward`
- 初始化方式：从统一 warm-start 基准 `TD3_velodyne_multi_v4` 初始化

## 训练过程

三车 Weighted08 对照设置了 `DRL_MULTI_MAX_EPOCHS=10`，训练在第 10 个 epoch 评估后自动停止。训练阶段 best checkpoint 出现在 epoch 9：

| Epoch | `success_rate` | `collision_rate` | `avg_reward` | `avg_env_steps` | `avg_final_distance` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.600` | `0.233` | `60.004` | `176.2` | `0.517` |
| 2 | `0.817` | `0.117` | `98.244` | `128.4` | `0.359` |
| 3 | `0.783` | `0.100` | `97.701` | `135.6` | `0.401` |
| 4 | `0.950` | `0.017` | `126.430` | `79.4` | `0.218` |
| 5 | `0.900` | `0.050` | `115.554` | `109.5` | `0.299` |
| 6 | `0.867` | `0.100` | `106.718` | `63.4` | `0.347` |
| 7 | `0.867` | `0.083` | `108.401` | `77.7` | `0.321` |
| 8 | `0.950` | `0.033` | `122.950` | `47.6` | `0.216` |
| 9 | `1.000` | `0.000` | `135.176` | `55.2` | `0.189` |
| 10 | `0.900` | `0.083` | `114.560` | `63.0` | `0.298` |

## 最终指标

| 指标 | 数值 |
| --- | ---: |
| `success_rate` | `0.924` |
| `collision_rate` | `0.046` |
| `full_success_rate` | `0.800` |
| `timeout_rate` | `0.090` |
| `success_80_rate` | `0.800` |
| `avg_reward` | `119.921` |
| `avg_final_distance` | `0.349` |
| `avg_episode_env_steps` | `71.2` |

累计计数：

- 单机器人成功：`832/900`
- 单机器人碰撞：`41/900`
- 三车全部成功 episode：`240/300`
- 至少 80% 机器人成功 episode：`240/300`
- timeout episode：`27/300`
- 发生碰撞 episode：`37/300`

## 结果解读

三车 Weighted08 对照在 best checkpoint 下完成了 300 episodes 测试，单机器人成功率为 `0.924`，三车全成功率为 `0.800`，碰撞率为 `0.046`。在当前三车主线中，该结果略优于共享 Policy Baseline，并明显优于 RewardOnly。

当前三车主线对比如下：

| 方法 | `success_rate` | `collision_rate` | `full_success_rate` | `timeout_rate` |
| --- | ---: | ---: | ---: | ---: |
| 三车共享 Policy Baseline | `0.926` | `0.056` | `0.797` | `0.053` |
| 三车 RewardOnly | `0.909` | `0.074` | `0.740` | `0.050` |
| 三车 Weighted08 | `0.924` | `0.046` | `0.800` | `0.090` |
| 三车局部邻域 Critic + Weighted08 | `0.913` | `0.052` | `0.747` | `0.100` |

该结果说明，当前三车场景中的主要收益更可能来自 Weighted08 reward，而不是现有局部邻域 Critic 结构。Weighted08 在不增加 actor 输入、不启用局部 critic 的情况下，已经达到当前最好的 full success 和 collision 表现。

因此，后续不能直接宣称“局部邻域 Critic 带来了提升”。更合理的下一步是回到实验组，优化局部邻域 Critic 的结构或训练方式，使其在同样 Weighted08 reward 下至少超过本对照组。

