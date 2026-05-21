# 三车几何邻域 Critic 扩展验证摘要

## 测试对象

- 模型：`TD3_velodyne_multi_v4_local_critic_geo_3_best`
- 场景：三车，`r1, r2, r3`
- 测试规模：300 episodes
- 测试阶段 reward：individual reward，仅用于统计策略表现
- Actor 输入：本车 24 维 observation
- Critic 训练输入：本车 observation + 几何局部邻居 context + 本车 action
- 初始化方式：从统一 warm-start 基准 `TD3_velodyne_multi_v4` 初始化

## 方法说明

该实验是三车局部邻域 Critic 的 geometry-only 变体。与原始三车局部邻域 Critic 的区别如下：

| 方法 | 每个邻居 context | 含义 |
| --- | --- | --- |
| 原始局部邻域 Critic | `relative_x, relative_y, distance, bearing, neighbor_linear_action, neighbor_angular_action, mask` | critic 同时看到邻居几何信息和邻居动作 |
| 几何邻域 Critic | `relative_x, relative_y, distance, bearing, mask` | critic 只看到邻居相对几何关系 |

两者 actor 执行阶段均只使用自身 24 维 observation，不使用通信，也不接收邻居信息。

## 训练过程

本次结果属于扩展验证：先按默认 10 epoch 训练，再从 latest checkpoint 继续到 20 epoch。继续训练时发现旧 checkpoint 的 epoch 计数会重复一次 epoch 10，因此本结果暂不直接并入 10 epoch 主表，而作为 20 epoch 扩展观察。

训练阶段 best checkpoint 出现在 extended 训练的 epoch 18：

| Epoch | `success_rate` | `collision_rate` | `avg_reward` | `avg_env_steps` | `avg_final_distance` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.217` | `0.483` | `-32.507` | `258.4` | `1.197` |
| 2 | `0.367` | `0.550` | `-12.708` | `175.7` | `1.639` |
| 3 | `0.400` | `0.383` | `-0.967` | `210.7` | `1.348` |
| 4 | `0.550` | `0.150` | `47.723` | `216.2` | `0.951` |
| 5 | `0.483` | `0.100` | `50.533` | `280.8` | `0.548` |
| 6 | `0.600` | `0.117` | `62.417` | `219.2` | `0.691` |
| 7 | `0.767` | `0.067` | `97.107` | `161.4` | `0.365` |
| 8 | `0.700` | `0.083` | `86.772` | `187.7` | `0.415` |
| 9 | `0.867` | `0.033` | `111.186` | `127.6` | `0.266` |
| 10 | `0.850` | `0.117` | `101.952` | `73.5` | `0.309` |
| 13 | `0.933` | `0.033` | `119.947` | `66.5` | `0.224` |
| 16 | `0.933` | `0.067` | `117.470` | `51.5` | `0.251` |
| 17 | `0.933` | `0.050` | `120.068` | `45.5` | `0.241` |
| 18 | `0.967` | `0.033` | `127.947` | `36.5` | `0.220` |
| 19 | `0.933` | `0.017` | `123.092` | `93.8` | `0.226` |
| 20 | `0.933` | `0.050` | `120.335` | `60.2` | `0.214` |

## 最终指标

| 指标 | 数值 |
| --- | ---: |
| `success_rate` | `0.937` |
| `collision_rate` | `0.053` |
| `full_success_rate` | `0.827` |
| `timeout_rate` | `0.010` |
| `avg_reward` | `119.518` |
| `avg_final_distance` | `0.340` |
| `avg_episode_env_steps` | `47.3` |

累计计数：

- 单机器人成功：`843/900`
- 单机器人碰撞：`48/900`
- 单机器人 timeout：`9/900`
- 三车全部成功 episode：`248/300`

## 结果解读

几何邻域 Critic 在 10 epoch 时尚未充分收敛，但扩展到 20 epoch 后表现明显提升。300 episodes 测试中，几何邻域 Critic 的 `full_success_rate=0.827`，高于当前三车 10 epoch 主线中的共享 Policy Baseline、RewardOnly、Weighted08 和原始局部邻域 Critic。

该结果说明，局部邻域 Critic 的有效信息可能主要来自邻居相对几何关系，而不是邻居动作。后续若将 20 epoch 作为正式训练预算，应将 Baseline、RewardOnly、Weighted08、原始局部邻域 Critic 和几何邻域 Critic 全部统一扩展到 20 epoch 后重新测试。

