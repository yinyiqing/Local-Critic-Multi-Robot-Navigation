# 三车共享 Policy Baseline best checkpoint 测试摘要

## 测试对象

- 模型：`TD3_velodyne_multi_v4_shared_policy_3_best`
- 场景：三车，`r1, r2, r3`
- 测试规模：300 episodes
- 测试阶段 reward：individual reward，仅用于统计策略表现
- Actor 输入：本车 24 维 observation
- 训练方式：多机器人共享同一个 actor/critic，不使用局部邻域 critic
- 初始化方式：从统一 warm-start 基准 `TD3_velodyne_multi_v4` 初始化

## 最终指标

| 指标 | 数值 |
| --- | ---: |
| `success_rate` | `0.926` |
| `collision_rate` | `0.056` |
| `full_success_rate` | `0.797` |
| `timeout_rate` | `0.053` |
| `success_80_rate` | `0.797` |
| `avg_reward` | `119.580` |
| `avg_final_distance` | `0.356` |
| `avg_episode_env_steps` | `48.4` |

累计计数：

- 单机器人成功：`833/900`
- 单机器人碰撞：`50/900`
- 三车全部成功 episode：`239/300`
- 至少 80% 机器人成功 episode：`239/300`
- timeout episode：`16/300`
- 发生碰撞 episode：`47/300`

## 结果解读

三车共享 Policy Baseline 在 best checkpoint 下完成了 300 episodes 测试，单机器人成功率达到 `0.926`，三车全成功率达到 `0.797`。该结果说明，在当前三车弱耦合场景中，仅使用共享 policy 并从统一基础导航模型 warm-start，就已经可以得到较强的多机器人导航能力。

这一结果是后续三车对照实验的重要基准。由于三车局部邻域 Critic 版本同时引入了距离加权协作 reward 和局部邻域 critic，后续仍需要补齐 reward-only 与 weighted08 对照，才能判断性能变化主要来自 reward 设计还是 critic 结构。

与当前三车局部邻域 Critic 的 300 episodes 结果相比，本 baseline 在 `success_rate` 和 `full_success_rate` 上略高，但 `collision_rate` 也略高：

| 方法 | `success_rate` | `collision_rate` | `full_success_rate` |
| --- | ---: | ---: | ---: |
| 三车共享 Policy Baseline | `0.926` | `0.056` | `0.797` |
| 三车局部邻域 Critic + weighted08 | `0.913` | `0.052` | `0.747` |

因此，当前三车场景下共享 policy baseline 是一个强对照组，不能被视为弱 baseline。局部邻域 Critic 的价值需要在 reward-only/weighted08 单变量对照，以及更高交互密度的 5 车或 10 车场景中继续验证。

## 20 epoch 扩展检查

为与几何邻域 Critic 的 20 epoch 扩展验证保持训练预算一致，三车共享 Policy Baseline 从原 10 epoch `latest` checkpoint 继续训练至 20 epoch。继续训练从 `Starting epoch: 11` 开始，未重新初始化模型，也未重复 epoch 10。

扩展训练日志：

- `train_multi_baseline_3_detached_20260521_135148_extended20.log`

扩展阶段 eval 结果如下：

| Epoch | `success_rate` | `collision_rate` | `avg_reward` | `avg_env_steps` | `avg_final_distance` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 11 | `0.850` | `0.067` | `103.746` | `114.7` | `0.327` |
| 12 | `0.917` | `0.050` | `116.619` | `71.7` | `0.355` |
| 13 | `0.950` | `0.033` | `124.210` | `70.0` | `0.255` |
| 14 | `0.867` | `0.100` | `106.895` | `74.5` | `0.375` |
| 15 | `0.717` | `0.117` | `83.084` | `172.6` | `0.424` |
| 16 | `0.850` | `0.067` | `103.507` | `117.7` | `0.373` |
| 17 | `0.617` | `0.050` | `73.051` | `256.1` | `0.553` |
| 18 | `0.817` | `0.083` | `102.208` | `123.8` | `0.335` |
| 19 | `0.367` | `0.017` | `35.447` | `300.0` | `0.634` |
| 20 | `0.833` | `0.017` | `105.871` | `174.4` | `0.364` |

扩展阶段没有出现新的 `Best checkpoint updated`，因此 best checkpoint 仍为原 10 epoch 阶段产生的模型。本实验不需要重新执行 300 episodes 测试，正式测试指标仍沿用上方结果。
