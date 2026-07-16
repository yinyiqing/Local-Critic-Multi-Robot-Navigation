# 五车 Weighted09 Active 测试总结

## 实验口径

- 初始模型：`TD3_velodyne_multi_v4`
- 训练模型：`TD3_velodyne_multi_v4_weighted09_active_5`
- 测试模型：`TD3_velodyne_multi_v4_weighted09_active_5_best`
- 训练日志：`train_multi_weighted09_active_5_detached_20260529_200614.log`
- 原始测试日志：`test_multi_weighted09_active_5_best_detached_20260531_120616.raw.log`
- 清洗测试日志：`test_multi_weighted09_active_5_best_300episodes_clean.log`
- 测试统计：`test_multi_weighted09_active_5_best_300episodes.npy`
- 场景：`standard`
- 机器人数量：5
- 测试集数：300 episodes

## 训练选择

训练共运行 20 epochs。best checkpoint 按 `full_success_rate` 选择，出现在 epoch 4：

| epoch | eval success_rate | eval collision_rate | eval unresolved_rate | eval full_success_rate | eval timeout_episode_rate | eval avg_reward | eval avg_env_steps | eval avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 0.940 | 0.040 | 0.020 | 0.750 | 0.150 | 117.599 | 63.8 | 0.224 |

epoch 4 之后评估指标明显退化。epoch 20 的 eval 为：

| epoch | eval success_rate | eval collision_rate | eval unresolved_rate | eval full_success_rate | eval timeout_episode_rate | eval avg_reward | eval avg_env_steps | eval avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 0.750 | 0.050 | 0.200 | 0.200 | 0.700 | 78.247 | 226.5 | 0.458 |

训练日志中，active-neighbor cooperative reward 几乎没有触发：721 个训练 episode 里只有 20 个 episode 的 `coop_agents` 非零，`mean_coop_neighbors=0.007`。这说明过滤 inactive/done 机器人后，旧 F 中很多 cooperative reward 混合很可能来自已经停止或完成的机器人。

## 300 Episodes 结果

| 指标 | 数值 |
| --- | ---: |
| success_rate | 0.874 |
| collision_rate | 0.071 |
| unresolved_rate | 0.055 |
| full_success_rate | 0.540 |
| timeout_episode_rate | 0.233 |
| total_success | 1311 / 1500 |
| total_collision | 107 / 1500 |
| total_unresolved | 82 / 1500 |
| total_full_success | 162 / 300 |
| timeout_episodes | 70 / 300 |
| avg_reward | 103.391 |
| avg_env_steps | 92.687 |
| avg_final_distance | 0.410 |

### 分布

| 指标 | 0 | 1 | 2 | 3 | 4 | 5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| success_hist | 0 | 1 | 8 | 32 | 97 | 162 |
| collision_hist | 212 | 72 | 13 | 3 | 0 | 0 |

## 与五车主线对比

| 方法 | success_rate | collision_rate | full_success_rate | avg_reward | avg_env_steps | avg_final_distance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 103.113 | 62.000 | 0.395 |
| B RewardOnly | 0.881 | 0.080 | 0.533 | 103.216 | 95.277 | 0.407 |
| E 纯几何邻域 Critic | 0.871 | 0.068 | 0.517 | 103.657 | 108.093 | 0.380 |
| F Weighted09 | 0.873 | 0.099 | 0.523 | 102.434 | 71.697 | 0.393 |
| H Weighted09 Active | 0.874 | 0.071 | 0.540 | 103.391 | 92.687 | 0.410 |

## 观察

- H 的 300 episodes `full_success_rate=0.540`，与 baseline 持平，略高于 F Weighted09 的 `0.523`。
- H 的 `collision_rate=0.071` 明显低于 baseline 和 F，说明 active-neighbor 过滤没有破坏避障安全性。
- H 的 `avg_env_steps=92.687` 和 `timeout_episode_rate=0.233` 偏高，说明策略仍有较明显的长尾未完成问题。
- 20 episodes eval 中 epoch 4 的 `full_success_rate=0.750` 没有在 300 episodes 测试中保持，说明五车场景下小样本 eval 容易高估策略稳定性。
- active 过滤后 cooperative reward 几乎消失，说明旧 F 的 cooperative 信号很可能大量来自 inactive/done 机器人；这个污染会改变 reward shaping，但去掉污染本身还不足以带来稳定优势。
