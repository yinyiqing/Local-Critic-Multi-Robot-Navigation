# 5 智能体扩展实验

本目录用于归档五车规模扩展实验。

## 当前状态

五车共享 Policy baseline 和 D2 几何邻域 Critic + Weighted08 已完成训练和 300 episodes 测试。该规模用于检验三车实验中表现较好的设置在机器人数量增加后是否仍然稳定。

## 计划优先级

优先考虑：

| 编号 | 方法 | 目的 |
| --- | --- | --- |
| A | 共享 Policy Baseline | 五车基础对照 |
| C | Weighted08 | 五车 reward shaping 对照 |
| D2 | 几何邻域 Critic + Weighted08 | 五车局部几何 critic 验证 |

是否补 B、C 和 D，取决于 A/D2 的结果是否需要更完整的横向解释。

## 当前结果

| 编号 | 方法 | success_rate | collision_rate | full_success_rate | 状态 |
| --- | --- | ---: | ---: | ---: | --- |
| A | 共享 Policy Baseline | 0.874 | 0.107 | 0.540 | 已完成 |
| C | Weighted08 | - | - | - | 待测 |
| D2 | 几何邻域 Critic + Weighted08 | 0.841 | 0.082 | 0.420 | 已完成 |

## 当前观察

- 五车 baseline 的整体完成效果优于 D2。
- D2 的碰撞率更低，但 success_rate 和 full_success_rate 更低，表现为更保守、完成更慢。
- 三车中 D2 优于 baseline，但五车标准场景未保持该优势，后续应优先检查五车密集场景或邻域 critic 参数设置。
