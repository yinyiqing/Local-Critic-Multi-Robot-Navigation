# 2 智能体机制验证

本目录保存两车阶段的机制验证实验。两车结果主要用于确认多车环境、共享 policy、动态 reward 和局部邻域 critic 的工程可行性，不作为当前实验主线横向比较的最终结果。

## 目录

| 目录 | 内容 |
| --- | --- |
| `A_共享PolicyBaseline/` | 两车共享 policy 验证 |
| `B_RewardOnly动态奖励对照/` | 两车 RewardOnly 动态奖励验证 |
| `C_Weighted08距离加权奖励对照/` | 两车 Weighted08 动态奖励验证 |
| `D_局部邻域Critic验证/` | 两车单邻居局部 critic 验证 |

当前正式横向对照见 `../3智能体/三车主线对照总表.md`。
