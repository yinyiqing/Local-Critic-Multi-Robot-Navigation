# 3 智能体主线实验

本目录保存当前实验主线的三车实验。所有主线实验统一从 `TD3_velodyne_multi_v4` warm-start，actor 执行阶段只使用本车 24 维 observation，测试阶段使用 300 episodes best actor 统计。

## 目录

| 编号 | 目录 | 方法 |
| --- | --- | --- |
| A | `A_共享PolicyBaseline/` | 三车共享 Policy Baseline |
| B | `B_RewardOnly动态奖励对照/` | 三车 RewardOnly |
| C | `C_Weighted08距离加权奖励对照/` | 三车 Weighted08 |
| D | `D_局部邻域Critic加Weighted08/` | 三车局部邻域 Critic + Weighted08 |
| D2 | `D2_几何邻域Critic加Weighted08/` | 三车几何邻域 Critic + Weighted08 |

横向结果见 `三车主线对照总表.md`。
