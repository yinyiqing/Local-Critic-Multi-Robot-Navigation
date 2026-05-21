# 多智能体实验归档

多智能体相关实验统一放在本目录。这里保存实验说明、阶段总结、关键训练日志和测试日志；正式模型、checkpoint 和结果数组仍保存在 `TD3/` 下，避免影响训练与测试脚本。

## 当前主线

当前论文主线是三车 CTDE 风格对照实验：

- actor 执行阶段只使用本车 24 维 observation。
- 执行阶段不通信，不读取邻居信息。
- 邻居信息只允许在训练阶段进入 critic。
- 三车主线统一从 `TD3_velodyne_multi_v4` warm-start。

主线横向表见：

- `三车主线实验矩阵.md`

## 目录

| 目录 | 内容 | 当前状态 |
| --- | --- | --- |
| `共享PolicyBaseline/` | 多机器人共享 actor/critic baseline | 三车主线完成，20 epoch 扩展未更新 best |
| `动态Reward/` | RewardOnly 对照，只改变训练 reward | 三车主线完成，20 epoch 扩展未更新 best |
| `动态RewardWeighted08/` | Weighted08 reward 对照 | 三车主线完成，20 epoch 扩展未更新 best |
| `局部邻域Critic/` | 局部 critic、几何 critic、容量验证 | D 与 D2 均完成，D2 当前最有论文价值 |

## 三车主线结果

| 方法 | `success_rate` | `collision_rate` | `full_success_rate` | 结论 |
| --- | ---: | ---: | ---: | --- |
| 三车共享 Policy Baseline | `0.926` | `0.056` | `0.797` | 强 baseline |
| 三车 RewardOnly | `0.909` | `0.074` | `0.740` | 粗糙协作 reward 退化 |
| 三车 Weighted08 | `0.924` | `0.046` | `0.800` | 强 reward shaping 对照 |
| 三车局部邻域 Critic | `0.913` | `0.052` | `0.747` | 邻居动作 context 未带来收益 |
| 三车几何邻域 Critic | `0.937` | `0.053` | `0.827` | 当前最好的三车全成功率 |

## 阅读建议

1. 先看 `三车主线实验矩阵.md`。
2. 再看各方向子目录的 `README.md`。
3. 最后进入具体三车实验目录查看 `*_summary.md` 和对应日志。

## 注意事项

- `logs/` 只保留正在运行的临时日志。
- 已完成实验应归档到对应 `experiments/多智能体/...` 子目录。
- 若扩展训练没有更新 best checkpoint，不需要重复执行 300 episodes test。
- 若正式改用 20 epoch 预算，应保证所有主线方法从各自 10 epoch `latest` checkpoint 继续到 20，而不是重新初始化。
