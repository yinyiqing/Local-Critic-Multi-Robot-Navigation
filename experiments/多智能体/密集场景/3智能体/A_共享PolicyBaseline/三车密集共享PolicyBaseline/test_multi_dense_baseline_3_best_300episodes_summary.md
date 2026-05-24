# 三车密集场景共享 Policy Baseline 测试总结

## 实验口径

- 模型：`TD3_velodyne_multi_v4_shared_policy_3_best`
- 测试脚本：`scripts/start_test_detached_multi_dense_baseline_3_best.sh`
- 原始日志：`test_multi_dense_baseline_3_best_detached_20260524_205520.raw.log`
- 清洗日志：`test_multi_dense_baseline_3_best_300episodes_clean.log`
- 场景：`dense`
- 机器人数量：3
- 测试集数：300 episodes

## 场景说明

该场景用于观察 3 个机器人在较小空间内分别到达各自目标时的交互表现。相比标准场景，起点和目标采样范围被缩小，因此该测试更偏向短程局部交互验证，不直接等同于更长路径的导航压力。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.993 |
| collision_rate | 0.004 |
| full_success_rate | 0.983 |
| total_success | 894 / 900 |
| total_collision | 4 / 900 |
| total_full_success | 295 / 300 |
| avg_reward | 118.142 |
| avg_env_steps | 23.473 |
| avg_final_distance | 0.273 |

## 观察

- baseline 在 3 智能体密集短程场景下表现很强，绝大多数 episode 可以三车全部到达目标。
- 失败样本主要表现为个别机器人未完成或发生碰撞，例如 episode 255 和 episode 272。
- 该结果说明 3 智能体密集短程场景对 baseline 的区分度可能有限，后续需要与 D2 以及更多机器人数量的密集场景一起对比。

