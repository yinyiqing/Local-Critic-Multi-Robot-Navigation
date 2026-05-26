# 五车密集场景几何邻域 Critic + Weighted08 测试总结

## 实验口径

- 模型：`TD3_velodyne_multi_v4_local_critic_geo_5_best`
- 测试脚本：`scripts/start_test_detached_multi_dense_local_critic_geo_5_best.sh`
- 原始日志：`test_multi_dense_local_critic_geo_5_best_detached_20260526_150725.raw.log`
- 清洗日志：`test_multi_dense_local_critic_geo_5_best_300episodes_clean.log`
- 场景：`dense`
- 机器人数量：5
- 测试集数：300 episodes

## 场景说明

该场景用于观察 5 个机器人在较小空间内分别到达各自目标时的交互表现。相比标准场景，起点和目标采样范围被缩小，因此该测试更偏向短程局部交互验证，不直接等同于更长路径的导航压力。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.948 |
| collision_rate | 0.011 |
| full_success_rate | 0.773 |
| total_success | 1422 / 1500 |
| total_collision | 16 / 1500 |
| total_full_success | 232 / 300 |
| avg_reward | 107.295 |
| avg_env_steps | 77.617 |
| avg_final_distance | 0.270 |

## 与五车密集 Baseline 对比

| 方法 | success_rate | collision_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.977 | 0.019 | 0.910 | 111.318 | 25.457 | 0.265 |
| D2 几何邻域 Critic + Weighted08 | 0.948 | 0.011 | 0.773 | 107.295 | 77.617 | 0.270 |

## 观察

- D2 的 collision_rate 低于 baseline，说明它在密集短程场景中也更少碰撞。
- D2 的 success_rate 和 full_success_rate 低于 baseline，尤其 full_success_rate 从 0.910 降到 0.773。
- D2 的 avg_env_steps 明显更高，说明它完成任务更慢，存在更多拖长或未完全完成的 episode。
- 五车 standard 和 dense 两个场景都显示同一趋势：D2 更保守、碰撞更少，但整体完成效率不如 baseline。
