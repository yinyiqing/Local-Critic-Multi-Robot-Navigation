# RewardOnly 动态奖励对照

本目录归档 RewardOnly 类动态 reward 对照实验。该类实验只改变训练阶段 reward，不改变 actor 输入，不启用局部邻域 critic。

当前目录结构：

```text
B_RewardOnly动态奖励对照/
├── 两车RewardOnly验证/
├── 三车RewardOnly/
├── 动态Reward实验计划.md
└── 动态Reward实验总结.md
```

## 实验口径

RewardOnly 的训练 reward 使用可见邻居 cooperative reward。测试阶段统一使用 individual reward 统计策略表现，便于和共享 Policy Baseline、Weighted08、局部邻域 Critic 横向比较。

三车主线均从统一 warm-start 基准 `TD3_velodyne_multi_v4` 初始化，actor 执行阶段保持本车 24 维 observation，不引入通信输入。

## 三车 RewardOnly 状态

三车 RewardOnly 已完成 300 episodes best checkpoint 测试，并从 10 epoch `latest` checkpoint 继续扩展到 20 epoch。扩展训练没有更新 best checkpoint，因此正式测试指标仍使用 epoch 6 best 模型。

关键文件：

- `三车RewardOnly/train_multi_reward_only_3_detached_20260520_194136.log`
- `三车RewardOnly/train_multi_reward_only_3_detached_20260521_170949_extended20.log`
- `三车RewardOnly/test_multi_reward_only_3_best_300episodes_summary.md`

## 三车主线位置

- 三车共享 Policy Baseline：`experiments/多智能体/A_共享Policy基线/三车共享PolicyBaseline/`
- 三车 RewardOnly：`experiments/多智能体/B_RewardOnly动态奖励对照/三车RewardOnly/`
- 三车 Weighted08：`experiments/多智能体/C_Weighted08距离加权奖励对照/`
- 三车局部邻域 Critic + Weighted08：`experiments/多智能体/D_局部邻域Critic加Weighted08/三车局部邻域Critic加Weighted08/`
- 三车几何邻域 Critic + Weighted08：`experiments/多智能体/D2_几何邻域Critic加Weighted08/三车几何邻域Critic加Weighted08/`
