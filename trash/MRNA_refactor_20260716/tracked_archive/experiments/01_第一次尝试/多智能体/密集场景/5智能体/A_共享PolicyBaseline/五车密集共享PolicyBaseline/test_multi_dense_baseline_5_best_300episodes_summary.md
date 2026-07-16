# 五车密集场景共享 Policy Baseline 测试总结

## 实验口径

- 模型：`TD3_velodyne_multi_v4_shared_policy_5_best`
- 测试脚本：`scripts/start_test_detached_multi_dense_baseline_5_best.sh`
- 原始日志：`test_multi_dense_baseline_5_best_detached_20260526_134022.raw.log`
- 清洗日志：`test_multi_dense_baseline_5_best_300episodes_clean.log`
- 场景：`dense`
- 机器人数量：5
- 测试集数：300 episodes

## 场景说明

该场景用于观察 5 个机器人在较小空间内分别到达各自目标时的交互表现。相比标准场景，起点和目标采样范围被缩小，因此该测试更偏向短程局部交互验证，不直接等同于更长路径的导航压力。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.977 |
| collision_rate | 0.019 |
| full_success_rate | 0.910 |
| total_success | 1466 / 1500 |
| total_collision | 29 / 1500 |
| total_full_success | 273 / 300 |
| avg_reward | 111.318 |
| avg_env_steps | 25.457 |
| avg_final_distance | 0.265 |

## 与五车标准场景 Baseline 对比

| 场景 | success_rate | collision_rate | full_success_rate | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: |
| standard | 0.874 | 0.107 | 0.540 | 62.000 | 0.395 |
| dense | 0.977 | 0.019 | 0.910 | 25.457 | 0.265 |

## 观察

- 五车 dense baseline 明显强于五车 standard baseline。
- 这说明当前 dense 设置虽然增加了局部交互，但也显著缩短了任务距离，使任务整体更容易完成。
- 后续需要与五车 dense D2 对比，判断几何邻域 critic 是否还能在短程密集交互中带来额外收益。
