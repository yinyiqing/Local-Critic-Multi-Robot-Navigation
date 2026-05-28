# 5 智能体扩展实验

本目录用于归档五车规模扩展实验。

## 当前状态

五车共享 Policy baseline、RewardOnly、Weighted08、D2 几何邻域 Critic + Weighted08、E 纯几何邻域 Critic 和 F Weighted09 已完成训练和 300 episodes 测试。该规模用于检验三车实验中表现较好的设置在机器人数量增加后是否仍然稳定。

## 计划优先级

优先考虑：

| 编号 | 方法 | 目的 |
| --- | --- | --- |
| A | 共享 Policy Baseline | 五车基础对照 |
| B | RewardOnly | 动态 reward 单独对照 |
| C | Weighted08 | 五车 reward shaping 对照 |
| D2 | 几何邻域 Critic + Weighted08 | 五车局部几何 critic 验证 |
| E | 纯几何邻域 Critic | 去掉 Weighted08 后单独验证 critic |
| F | Weighted09 | 降低邻居 reward 权重后的距离加权 reward 对照 |

当前 A/B/C/D2/E/F 已补齐，可用于判断五车 D2 下降主要来自 reward 设计还是 critic 结构，并初步验证邻居 reward 权重是否偏高。

## 当前结果

| 编号 | 方法 | success_rate | collision_rate | full_success_rate | 状态 |
| --- | --- | ---: | ---: | ---: | --- |
| A | 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 已完成 |
| B | RewardOnly | 0.881 | 0.080 | 0.533 | 已完成 |
| C | Weighted08 | 0.849 | 0.057 | 0.447 | 已完成 |
| D2 | 几何邻域 Critic + Weighted08 | 0.841 | 0.082 | 0.420 | 已完成 |
| E | 纯几何邻域 Critic | 0.871 | 0.068 | 0.517 | 已完成 |
| F | Weighted09 | 0.873 | 0.099 | 0.523 | 已完成 |

## 当前观察

- 五车 baseline 的整体完成效果优于 D2。
- RewardOnly 与 baseline 接近，个体成功率略高、碰撞率更低，但全成功率略低。
- Weighted08 的碰撞率最低，但 success_rate 和 full_success_rate 明显下降，avg_env_steps 增加，表现为更保守、完成更慢。
- D2 与 Weighted08 趋势接近，说明五车 D2 的下降主要来自 Weighted08 带来的目标驱动力削弱，几何邻域 critic 没有抵消这个问题。
- E 纯几何邻域 Critic 接近 baseline，明显优于 C/D2 的 full_success_rate，说明几何邻域 critic 单独不是主要问题。
- F Weighted09 明显优于 Weighted08，说明 `0.2` 的邻居 reward 权重偏强；但 F 仍未超过 baseline，只是更接近 baseline。
- 三车中 D2 优于 baseline，但五车标准场景未保持该优势。后续若继续优化五车，应优先调整 reward 权重、邻域范围或场景压力，而不是直接扩大到更多机器人。
