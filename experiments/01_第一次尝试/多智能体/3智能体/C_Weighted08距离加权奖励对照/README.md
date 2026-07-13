# Weighted08 距离加权奖励对照

本目录归档 `weighted08` 类动态 reward 对照实验。该类实验只改变训练阶段 reward，不启用局部邻域 critic。

当前目录结构：

```text
C_Weighted08距离加权奖励对照/
├── README.md
└── 三车Weighted08/
```

## 实验口径

训练阶段使用距离加权的邻居 reward：

```text
reward_i = 0.8 * own_reward_i + 0.2 * distance_weighted_neighbor_reward_i
```

如果当前机器人没有可见邻居，则退化为自身 reward。测试阶段统一使用 individual reward 统计策略表现，便于和共享 Policy Baseline、RewardOnly、局部邻域 Critic 横向比较。

三车主线均从统一 warm-start 基准 `TD3_velodyne_multi_v4` 初始化，actor 执行阶段保持本车 24 维 observation，不引入通信输入。

## 三车主线位置

- 三车共享 Policy Baseline：`experiments/01_第一次尝试/多智能体/3智能体/A_共享PolicyBaseline/三车共享PolicyBaseline/`
- 三车 RewardOnly：`experiments/01_第一次尝试/多智能体/3智能体/B_RewardOnly动态奖励对照/三车RewardOnly/`
- 三车 Weighted08：`experiments/01_第一次尝试/多智能体/3智能体/C_Weighted08距离加权奖励对照/三车Weighted08/`
- 三车局部邻域 Critic + Weighted08：`experiments/01_第一次尝试/多智能体/3智能体/D_局部邻域Critic加Weighted08/三车局部邻域Critic加Weighted08/`
- 三车几何邻域 Critic + Weighted08：`experiments/01_第一次尝试/多智能体/3智能体/D2_几何邻域Critic加Weighted08/三车几何邻域Critic加Weighted08/`
