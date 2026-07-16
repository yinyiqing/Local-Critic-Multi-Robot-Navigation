# 三车密集场景几何邻域 Critic + Weighted08 测试总结

## 实验口径

- 模型：`TD3_velodyne_multi_v4_local_critic_geo_3_best`
- 测试脚本：`scripts/start_test_detached_multi_dense_local_critic_geo_3_best.sh`
- 原始日志：`test_multi_dense_local_critic_geo_3_best_detached_20260524_210948.raw.log`
- 清洗日志：`test_multi_dense_local_critic_geo_3_best_300episodes_clean.log`
- 场景：`dense`
- 机器人数量：3
- 测试集数：300 episodes

## 场景说明

该场景用于观察 3 个机器人在较小空间内分别到达各自目标时的交互表现。相比标准场景，起点和目标采样范围被缩小，因此该测试更偏向短程局部交互验证，不直接等同于更长路径的导航压力。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.996 |
| collision_rate | 0.001 |
| full_success_rate | 0.987 |
| total_success | 896 / 900 |
| total_collision | 1 / 900 |
| total_full_success | 296 / 300 |
| avg_reward | 117.667 |
| avg_env_steps | 25.660 |
| avg_final_distance | 0.273 |

## 与密集 Baseline 简要对比

| 方法 | success_rate | collision_rate | full_success_rate |
| --- | ---: | ---: | ---: |
| 共享 Policy Baseline | 0.993 | 0.004 | 0.983 |
| 几何邻域 Critic + Weighted08 | 0.996 | 0.001 | 0.987 |

## 观察

- D2 在 3 智能体密集短程场景下小幅优于 baseline，主要体现在碰撞更少、全成功率略高。
- 两组结果都很高，说明 3 智能体密集短程场景区分度有限。
- 后续更关键的是 5 智能体和更高密度场景下是否还能保持稳定优势。

