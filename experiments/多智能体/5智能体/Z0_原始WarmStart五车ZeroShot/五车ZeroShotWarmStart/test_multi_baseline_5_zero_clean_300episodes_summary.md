# 五车 ZeroShot WarmStart 测试总结

## 实验口径

- 测试模型：`TD3_velodyne_multi_v4`
- 五车训练：无
- 原始测试日志：`test_multi_baseline_5_zero_clean_detached_20260529_153256.raw.log`
- 清洗测试日志：`test_multi_baseline_5_zero_clean_300episodes_clean.log`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.821 |
| collision_rate | 0.109 |
| unresolved_rate | 0.070 |
| full_success_rate | 0.400 |
| total_success | 1232 / 1500 |
| total_collision | 163 / 1500 |
| total_unresolved | 105 / 1500 |
| total_full_success | 120 / 300 |
| avg_reward | 92.852 |
| avg_env_steps | 140.890 |
| avg_final_distance | 0.465 |
| 300-step episode rate | 0.303 |
| 300-step episodes | 91 / 300 |

## 与五车主线对比

| 方法 | success_rate | collision_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Z0 原始 WarmStart ZeroShot | 0.821 | 0.109 | 0.400 | 92.852 | 140.890 | 0.465 |
| A 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 103.113 | 62.000 | 0.395 |
| B RewardOnly | 0.881 | 0.080 | 0.533 | 103.216 | 95.277 | 0.407 |
| E 纯几何邻域 Critic | 0.871 | 0.068 | 0.517 | 103.657 | 108.093 | 0.380 |
| F Weighted09 | 0.873 | 0.099 | 0.523 | 102.434 | 71.697 | 0.393 |

## 观察

- Z0 明显低于 A/B/E/F，说明五车训练确实改善了原始 warm-start 的五车适应性。
- Z0 的 avg_env_steps 明显高于 A 和 F，且 300-step episode 比例达到 0.303，说明原始模型在五车中容易出现慢速绕行、犹豫或局部死锁。
- Z0 的 collision_rate 与 A 接近，但 success_rate 和 full_success_rate 明显更低，说明问题不只是碰撞，还包括未完成和效率不足。
