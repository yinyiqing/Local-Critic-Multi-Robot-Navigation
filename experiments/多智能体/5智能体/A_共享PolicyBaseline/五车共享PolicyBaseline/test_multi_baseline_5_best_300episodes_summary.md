# 五车共享 Policy Baseline 测试总结

## 实验口径

- 初始模型：`TD3_velodyne_multi_v4`
- 训练模型：`TD3_velodyne_multi_v4_shared_policy_5`
- 测试模型：`TD3_velodyne_multi_v4_shared_policy_5_best`
- 训练日志：`train_multi_baseline_5_detached_20260524_215027.log`
- 原始测试日志：`test_multi_baseline_5_best_detached_20260525_195558.raw.log`
- 清洗测试日志：`test_multi_baseline_5_best_300episodes_clean.log`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 训练选择

训练共运行 20 epochs。best checkpoint 出现在 epoch 2：

| epoch | eval success_rate | eval collision_rate | eval avg_reward |
| ---: | ---: | ---: | ---: |
| 2 | 0.890 | 0.080 | 105.849 |

后续 epoch 评估指标有波动并下降，因此测试使用 epoch 2 的 best 模型，而不是 latest 模型。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.874 |
| collision_rate | 0.107 |
| full_success_rate | 0.540 |
| total_success | 1311 / 1500 |
| total_collision | 161 / 1500 |
| total_full_success | 162 / 300 |
| avg_reward | 103.113 |
| avg_env_steps | 62.000 |
| avg_final_distance | 0.395 |

## 观察

- 5 智能体 baseline 能稳定完成 300 episodes 测试，说明修复后的 5 车 reset 和仿真流程可用于后续对照。
- 相比 3 智能体，个体成功率和全成功率明显下降，碰撞率明显上升，说明 5 车场景确实带来了更强的多机器人交互压力。
- full_success_rate 为 0.540，表示接近一半 episode 里至少有一辆车失败或碰撞。这个结果为后续 D2 提供了清晰对照空间。

