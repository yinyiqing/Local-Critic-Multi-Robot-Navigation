# 5 智能体密集场景

本目录用于归档五车 dense case 测试结果。

## 当前状态

五车密集场景已完成共享 Policy Baseline 和 D2 几何邻域 Critic + Weighted08 两组直接对照。

## 计划方法

| 编号 | 方法 | 状态 |
| --- | --- | --- |
| A | 共享 Policy Baseline | 已完成 |
| C | Weighted08 | 待定 |
| D2 | 几何邻域 Critic + Weighted08 | 已完成 |

## 当前结果

| 编号 | 方法 | success_rate | collision_rate | full_success_rate | 状态 |
| --- | --- | ---: | ---: | ---: | --- |
| A | 共享 Policy Baseline | 0.977 | 0.019 | 0.910 | 已完成 |
| D2 | 几何邻域 Critic + Weighted08 | 0.948 | 0.011 | 0.773 | 已完成 |

## 观察

五车 dense baseline 明显强于五车 standard baseline，说明当前 dense 设置更偏短程局部交互验证，并不一定比标准场景更难。

D2 在 dense 中仍低于 baseline：碰撞率更低，但 success_rate、full_success_rate 和完成效率下降。这与五车 standard 的趋势一致。
