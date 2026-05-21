# 三车 RewardOnly best checkpoint 测试摘要

## 测试对象

- 模型：`TD3_velodyne_multi_v4_reward_only_3_best`
- 场景：三车，`r1, r2, r3`
- 测试规模：300 episodes
- 测试阶段 reward：individual reward，仅用于统计策略表现
- Actor 输入：本车 24 维 observation
- Critic 输入：本车 24 维 observation，不使用局部邻域 context
- 训练 reward：启用可见邻居 cooperative reward，不启用距离加权 reward
- 初始化方式：从统一 warm-start 基准 `TD3_velodyne_multi_v4` 初始化

## 训练过程

RewardOnly 对照先训练到第 10 个 epoch 后停止。训练阶段 best checkpoint 出现在 epoch 6：

| Epoch | `success_rate` | `collision_rate` | `avg_reward` |
| ---: | ---: | ---: | ---: |
| 1 | `0.483` | `0.367` | `24.260` |
| 2 | `0.633` | `0.200` | `68.513` |
| 3 | `0.817` | `0.067` | `105.873` |
| 4 | `0.817` | `0.117` | `93.499` |
| 5 | `0.900` | `0.100` | `111.459` |
| 6 | `0.967` | `0.033` | `126.217` |
| 7 | `0.900` | `0.067` | `114.201` |
| 8 | `0.833` | `0.133` | `100.549` |
| 9 | `0.867` | `0.017` | `114.997` |
| 10 | `0.867` | `0.050` | `111.503` |

为与几何邻域 Critic 的 20 epoch 扩展验证保持训练预算一致，RewardOnly 从原 10 epoch `latest` checkpoint 继续训练至 20 epoch。继续训练从 `Starting epoch: 11` 开始，未重新初始化模型，也未重复 epoch 10。

扩展训练结果如下：

| Epoch | `success_rate` | `collision_rate` | `avg_reward` |
| ---: | ---: | ---: | ---: |
| 11 | `0.733` | `0.083` | `86.546` |
| 12 | `0.733` | `0.050` | `86.496` |
| 13 | `0.850` | `0.033` | `105.846` |
| 14 | `0.483` | `0.067` | `50.171` |
| 15 | `0.633` | `0.083` | `69.099` |
| 16 | `0.883` | `0.000` | `114.428` |
| 17 | `0.717` | `0.083` | `84.214` |
| 18 | `0.717` | `0.100` | `79.191` |
| 19 | `0.700` | `0.033` | `83.169` |
| 20 | `0.833` | `0.067` | `101.185` |

扩展到 20 epoch 后没有更新 best checkpoint，最高评估仍然是 10 epoch 内的 epoch 6。因此无需重新运行 300 episodes 测试，下面正式测试指标仍对应 epoch 6 best 模型。

## 最终指标

| 指标 | 数值 |
| --- | ---: |
| `success_rate` | `0.909` |
| `collision_rate` | `0.074` |
| `full_success_rate` | `0.740` |
| `timeout_rate` | `0.050` |
| `success_80_rate` | `0.740` |
| `avg_reward` | `113.364` |
| `avg_final_distance` | `0.373` |
| `avg_episode_env_steps` | `63.8` |

累计计数：

- 单机器人成功：`818/900`
- 单机器人碰撞：`67/900`
- 三车全部成功 episode：`222/300`
- 至少 80% 机器人成功 episode：`222/300`
- timeout episode：`15/300`
- 发生碰撞 episode：`64/300`

## 结果解读

三车 RewardOnly 对照在 best checkpoint 下完成了 300 episodes 测试，单机器人成功率为 `0.909`，三车全成功率为 `0.740`。该结果低于三车共享 Policy Baseline，也略低于当前三车局部邻域 Critic + Weighted08 结果。

这说明在当前三车弱耦合场景中，仅将训练 reward 改为可见邻居 cooperative reward 并不能带来稳定收益。RewardOnly 在早期训练阶段出现过明显性能下降，随后恢复到可用水平，但最终 300 episodes 测试中碰撞率高于 baseline 和局部邻域 Critic。

当前三车主线对比如下：

| 方法 | `success_rate` | `collision_rate` | `full_success_rate` |
| --- | ---: | ---: | ---: |
| 三车共享 Policy Baseline | `0.926` | `0.056` | `0.797` |
| 三车 RewardOnly | `0.909` | `0.074` | `0.740` |
| 三车局部邻域 Critic + Weighted08 | `0.913` | `0.052` | `0.747` |

因此，RewardOnly 不是一个足够强的改进方向，但它作为对照组是必要的：它表明直接引入邻居 cooperative reward 可能带来更高碰撞风险，后续需要继续测试 Weighted08，以判断距离加权 reward 是否能缓解粗糙 cooperative reward 的信用分配问题。
