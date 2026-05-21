# 动态 Reward Weighted08 实验

本目录归档 `weighted08` 类动态 reward 对照实验。该类实验只改变训练阶段 reward，不启用局部邻域 critic。

当前目录结构：

```text
动态RewardWeighted08/
├── 两车Weighted08验证/
├── 三车Weighted08/
├── 实验计划.md
└── 实验总结.md
```

## 实验口径

训练阶段使用距离加权的邻居 reward：

```text
reward_i = 0.8 * own_reward_i + 0.2 * distance_weighted_neighbor_reward_i
```

如果当前机器人没有可见邻居，则退化为自身 reward。测试阶段统一使用 individual reward 统计策略表现，便于和共享 Policy Baseline、RewardOnly、局部邻域 Critic 横向比较。

三车主线均从统一 warm-start 基准 `TD3_velodyne_multi_v4` 初始化，actor 执行阶段保持本车 24 维 observation，不引入通信输入。

## 三车主线位置

- 三车共享 Policy Baseline：`experiments/多智能体/共享PolicyBaseline/三车共享PolicyBaseline/`
- 三车 RewardOnly：`experiments/多智能体/动态Reward/三车RewardOnly/`
- 三车 Weighted08：`experiments/多智能体/动态RewardWeighted08/三车Weighted08/`
- 三车局部邻域 Critic + Weighted08：`experiments/多智能体/局部邻域Critic/三车多邻居验证/`

