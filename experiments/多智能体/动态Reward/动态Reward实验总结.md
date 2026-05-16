# 多智能体动态 Reward 实验总结

## 结论

这一轮实验是对原始动态 reward 想法的直接实现：在共享 policy 多智能体训练基础上，加入“雷达感知范围内机器人 reward 平均”的动态 reward，并完成了训练和独立测试。

结论是：这个版本可以跑通，也能维持较低碰撞率，但整体效果没有明显超过普通多智能体共享 policy baseline。它有一定协同倾向，主要体现在碰撞率较低；但双车同时成功率和到达效率不够稳定，很多 episode 跑满 300 步仍没有完成任务。

因此保留这个实验，但把它定位为“原始动态 reward 方案对照/负结果”，而不是最终主结果。

## 实验设置

- 实验版本：`multi-agent-shared-policy-v4-coop`
- 模型名：`TD3_velodyne_multi_v4_coop`
- 训练方式：两个机器人在同一个 Gazebo 环境中运行，共享同一个 TD3 actor/critic
- 动态 reward：训练阶段开启局部 reward 平均
- 测试阶段：关闭动态 reward，用原始 individual reward 统计，方便与 baseline 比较
- 机器人数量：2
- 测试 episode 上限：300 steps

产物位置：

- 训练日志：`logs/train_multi_coop_detached_20260515_132917.log`
- 测试日志：
  - `logs/test_multi_coop_detached_20260515_172302.log`
  - `logs/test_multi_coop_detached_20260515_235510.log`
- 模型文件：`TD3/pytorch_models/TD3_velodyne_multi_v4_coop_actor.pth`
- checkpoint：`TD3/checkpoints/TD3_velodyne_multi_v4_coop_latest.pt`
- 测试结果：`TD3/results/TD3_velodyne_multi_v4_coop_test.npy`

## 训练结果

训练跑到 `Eval Epoch 23`。过程中出现过不错的高峰，但稳定性不足。

代表性评估结果：

| Epoch | Success Rate | Collision Rate | Avg Reward | Avg Final Distance |
| --- | ---: | ---: | ---: | ---: |
| 9 | 0.950 | 0.000 | 124.005 | 0.318 |
| 15 | 0.900 | 0.050 | 111.684 | 0.221 |
| 18 | 0.800 | 0.000 | 92.383 | 0.409 |
| 19 | 0.950 | 0.000 | 120.752 | 0.293 |
| 21 | 0.850 | 0.100 | 105.136 | 0.373 |
| 22 | 0.600 | 0.100 | 58.161 | 0.714 |
| 23 | 0.600 | 0.150 | 52.678 | 0.547 |

训练阶段判断：

- `Epoch 9` 和 `Epoch 19` 都达到 `success_rate=0.95`、`collision_rate=0.0`，说明动态 reward 版本确实有能力学到较好的策略。
- 但后续 `Epoch 20/22/23` 明显回落，说明策略不稳定。
- 这一轮只保存了 `latest` checkpoint，没有保存 best checkpoint，因此不能回到 `Epoch 9` 或 `Epoch 19` 的最佳权重。

## 测试结果

动态 reward 版本测试最终跑到 `2183` 个 episode。

整体统计：

| 指标 | 数值 |
| --- | ---: |
| Episode 数 | 2183 |
| Success Rate | 0.699 |
| Collision Rate | 0.057 |
| Full Success Rate | 0.490 |
| Avg Reward | 74.0 |
| Avg Final Distance | 0.615 |
| Timeout 300 Rate | 0.432 |

分段统计：

| 区间 | Success Rate | Collision Rate | Full Success Rate | Avg Reward | Timeout Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 前 120 episode | 0.767 | 0.050 | 0.625 | 85.7 | 0.308 |
| 121+ episode | 0.695 | 0.057 | 0.482 | 73.3 | 0.439 |
| 最后 100 episode | 0.735 | 0.035 | 0.540 | 83.4 | 0.400 |
| 最后 200 episode | 0.715 | 0.043 | 0.525 | 78.6 | 0.405 |
| 最后 500 episode | 0.680 | 0.055 | 0.480 | 70.7 | 0.444 |

测试阶段判断：

- 碰撞率整体较低，约 `5.7%`，最后 100/200 episode 还下降到 `3.5%~4.3%`。
- 但成功率整体约 `69.9%`，双车同时成功率约 `49.0%`，弱于普通多智能体 baseline 和后续 weighted08。
- `Timeout 300 Rate = 43.2%`，说明很多 episode 不是撞了，而是至少一辆车迟迟到不了目标。
- 因此，这一版动态 reward 更像是降低了一部分碰撞风险，但没有稳定提升任务完成效率。

## 与普通多智能体 Baseline 对比

普通多智能体 baseline `TD3_velodyne_multi_v4` 的 300 episode 公平长测试结果：

- `success_rate = 0.792`
- `collision_rate = 0.117`
- `full_success_rate = 0.603`
- `timeout_rate = 0.180`
- `avg_reward = 86.951`

动态 reward 完全平均版本整体测试：

- `success_rate = 0.699`
- `collision_rate = 0.057`
- `full_success_rate = 0.490`
- `timeout_rate = 0.432`
- `avg_reward = 74.0`

结论：完全平均动态 reward 完成了可行性验证，但暂时不能替代普通多智能体 baseline。它的价值在于揭示了一个问题：直接平均 reward 会降低碰撞，但也可能削弱个体目标驱动，造成大量 timeout。

## 可能原因

1. 只有两辆机器人时，局部 reward 平均带来的协同信息有限。
2. 当一辆车失败或接近碰撞时，另一辆车的 reward 会被拉低，训练信号更噪。
3. 当前 observation 没有显式加入其他机器人状态，policy 很难准确判断“为什么邻居 reward 变化”。
4. 动态 reward 使用直接平均，可能削弱了个体到达目标的动力。
5. 这一轮没有保存 best checkpoint，训练高峰权重被后续 latest 覆盖。

## 下一步建议

优先保留普通多智能体 baseline 作为主线结果。这个动态 reward 完全平均版本作为探索性实验和负结果写入报告，但不把它作为最终最优版本。

后续如果继续优化动态 reward，可以按以下顺序：

1. 增加 best checkpoint 保存，避免错过 `Epoch 9/19` 这类高峰模型。
2. 将 reward 从完全平均改为加权形式：

```text
reward_i = 0.8 * own_reward_i + 0.2 * mean(neighbor_rewards)
```

3. 在 observation 中加入邻近机器人距离/方位等信息，让 policy 有能力解释协同 reward。
4. 对 timeout 单独加惩罚或增加时间效率项，减少“低碰撞但到不了”的情况。
5. 等两车版本稳定后，再考虑三车或更多机器人，否则车辆数量增加会放大训练噪声。

## 总结

已经完成从单智能体到多智能体共享 policy 的扩展，并进一步实现了基于局部感知范围的动态 reward 机制。动态 reward 完全平均版本能够正常训练和测试，在部分 epoch 中达到较高成功率和零碰撞，说明该机制具备一定可行性；但长时间测试显示其整体成功率和双车同时成功率不如普通多智能体 baseline，主要问题是 episode timeout 较多、策略稳定性不足。这个结果推动进一步尝试 best checkpoint、加权 reward 融合和更充分的邻居状态观测。
