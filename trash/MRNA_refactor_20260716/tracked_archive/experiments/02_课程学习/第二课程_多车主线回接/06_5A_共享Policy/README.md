# 06_5A_共享Policy

## 定位

这是主线从三车几何局部 Critic 模型扩展到五车共享 Policy 的实验：

`3D2_几何邻域Critic best -> 5A_共享Policy`

这里的 5A 仍然是共享 actor、无局部 Critic 的五车标准场景，用来确认课程主线能否从三车迁移到五车。

## 训练设置

- 训练模型：`TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded`
- 初始模型：`TD3_velodyne_multi_v4_curriculum_stage2_to_3d2_geo_critic_from_3a_guarded_best`
- 继承方式：只继承 actor，critic 重新初始化
- 机器人数量：5
- 场景：`standard`
- 奖励：individual
- 局部 Critic：关闭
- actor lr：`2e-6`
- critic lr：`2e-5`
- actor 延迟更新：`20000` agent samples
- eval：每次 40 episodes
- best 指标：`full_success`

训练日志：

- `logs/train/train_multi_stage2_to_5a_shared_guarded_detached_20260608_175632.log`

## 训练观察

训练中最好的 eval 出现在 epoch 4：

| epoch | success_rate | collision_rate | full_success_rate |
| ---: | ---: | ---: | ---: |
| 4 | 0.920 | 0.065 | 0.725 |
| 5 | 0.790 | 0.110 | 0.300 |
| 6 | 0.675 | 0.255 | 0.125 |

epoch 4 附近 actor 刚开始解冻，后续继续更新 actor 后指标明显下降。因此保留并测试 `best`，不使用 latest。

## 300 Episodes 测试

测试模型：

`TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best`

测试日志：

- `logs/test/test_multi_stage2_to_5a_shared_guarded_TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best_detached_20260608_203601.log`

结果：

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.897 |
| collision_rate | 0.087 |
| unresolved_rate | 0.018 |
| full_success_rate | 0.600 |
| timeout_episode_rate | 0.087 |
| total_success | 1345 / 1500 |
| total_collision | 131 / 1500 |
| total_unresolved | 27 / 1500 |
| total_full_success | 180 / 300 |
| timeout_episodes | 26 / 300 |

## 与旧 5A 对比

| 模型 | success_rate | collision_rate | full_success_rate |
| --- | ---: | ---: | ---: |
| 旧 5A | 0.874 | 0.107 | 0.540 |
| 新 5A | 0.897 | 0.087 | 0.600 |

结论：新 5A 比旧 5A 有稳定提升，但提升幅度不大。它可以作为新的五车主线起点。

## 后续

下一步已启动：

`5A best -> 5D_几何局部Critic`

注意：不再用 `5D2` 这个名字，避免和旧实验里的 D2 概念混淆。
