# 局部邻域 Critic 实验目录

本目录归档 CTDE 风格局部邻域 Critic 实验。核心约束是：actor 执行阶段只使用本车 24 维 observation；邻居信息只允许在训练阶段进入 critic。

## 方法关系

| 方法 | 子目录 | critic 邻居 context | 当前角色 |
| --- | --- | --- | --- |
| 两车单邻居验证 | `两车单邻居验证/` | 单邻居 context | 工程机制验证 |
| 三车局部邻域 Critic | `三车多邻居验证/` | 几何 + 邻居动作 + mask | D，作为消融保留 |
| 三车几何邻域 Critic | `三车几何邻域Critic扩展验证/` | 几何 + mask | D2，当前主方法候选 |
| 容量验证 | `容量验证/` | 无训练 | 检查 2/3/5/10 车环境可运行性 |

## D 与 D2 的区别

原始 D 每个邻居提供 7 维 context：

```text
relative_x, relative_y, distance, bearing,
neighbor_linear_action, neighbor_angular_action, mask
```

D2 每个邻居提供 5 维 context：

```text
relative_x, relative_y, distance, bearing, mask
```

D2 更符合“局部几何邻域 critic”的论文叙事：critic 学习相对空间关系，而不是额外依赖邻居动作。

## 当前三车结果

| 方法 | `success_rate` | `collision_rate` | `full_success_rate` | `timeout_rate` | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| D. 局部邻域 Critic | `0.913` | `0.052` | `0.747` | `0.100` | 没有超过 Weighted08 |
| D2. 几何邻域 Critic | `0.937` | `0.053` | `0.827` | `0.010` | 当前三车全成功率最好 |

## 关键文件

```text
三车多邻居验证/test_multi_local_critic_3_best_300episodes_summary.md
三车几何邻域Critic扩展验证/test_multi_local_critic_geo_3_best_300episodes_summary.md
三车多邻居验证/train_multi_local_critic_3_detached_20260521_193351_extended20.log
三车几何邻域Critic扩展验证/train_multi_local_critic_geo_3_extended20.raw.log
环境容量验证.md
```

## 当前判断

- D 不建议删除。它是必要消融，用来说明“critic 看到邻居动作并不一定更好”。
- D2 更适合作为论文主方法候选。
- D 的 20 epoch 扩展检查已完成，未更新 best checkpoint，正式测试仍使用 epoch 8 best。
- 若三车差距仍不够强，应优先扩展到 5 车和 10 车。
