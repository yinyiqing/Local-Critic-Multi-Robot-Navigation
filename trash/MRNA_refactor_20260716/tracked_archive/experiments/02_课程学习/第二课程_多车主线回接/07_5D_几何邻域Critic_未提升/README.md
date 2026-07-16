# 07_5D_几何邻域Critic_未提升

## 定位

这是从新 5A best 出发的五车几何邻域 Critic 对照实验：

`5A_共享Policy best -> 5D_几何邻域Critic`

目标是验证“训练阶段向 critic 开放多机局部几何信息”是否能在五车标准场景上继续提升。

## 训练设置

- 训练模型：`TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded`
- 初始模型：`TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best`
- 继承方式：只继承 actor，critic 重新初始化
- 机器人数量：5
- 场景：`standard`
- critic：几何邻域局部 Critic
- actor 输入维度：不变
- actor lr：`1e-6`
- critic lr：`8e-5`
- actor 延迟更新：`20000` agent samples
- max epochs：6
- eval：40 episodes

训练日志：

- `logs/train/train_multi_stage2_to_5d_geo_critic_from_5a_guarded_detached_20260608_220920.log`

## 训练结果

| epoch | success_rate | collision_rate | full_success_rate |
| ---: | ---: | ---: | ---: |
| 1 | 0.890 | 0.090 | 0.625 |
| 2 | 0.920 | 0.070 | 0.700 |
| 3 | 0.870 | 0.105 | 0.600 |
| 4 | 0.890 | 0.090 | 0.600 |
| 5 | 0.885 | 0.095 | 0.525 |
| 6 | 0.850 | 0.115 | 0.475 |

best 出现在 epoch 2。后续继续训练后 full success 下降，说明 actor 继续更新后仍然存在退化。

## 300 Episodes 测试

测试模型：

`TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best`

测试日志：

- `logs/test/test_multi_stage2_to_5d_geo_critic_from_5a_guarded_best_TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best_detached_20260609_093904.log`

结果：

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.893 |
| collision_rate | 0.086 |
| unresolved_rate | 0.023 |
| full_success_rate | 0.590 |
| timeout_episode_rate | 0.107 |
| total_success | 1339 / 1500 |
| total_collision | 129 / 1500 |
| total_unresolved | 34 / 1500 |
| total_full_success | 177 / 300 |

## 与新 5A 对比

| 模型 | success_rate | collision_rate | full_success_rate |
| --- | ---: | ---: | ---: |
| 新 5A | 0.897 | 0.087 | 0.600 |
| 新 5D | 0.893 | 0.086 | 0.590 |

结论：几何邻域 Critic 没有带来实质提升。它可以作为对照保留，但不继续作为当前主线推进。

当前主线回到新 5A，并对它做人工密集 case 诊断。
