# 3 智能体密集场景

本目录用于归档三车密集场景测试结果。

## 场景口径

- 机器人数量：3
- 每辆机器人仍有独立目标
- 起点采样范围缩小到中心区域
- 目标点相对起点的随机 offset 缩小
- 执行阶段 actor 输入不变，仍只使用本车 observation
- 测试规模优先使用 300 episodes

## 待补实验

| 编号 | 方法 | 状态 |
| --- | --- | --- |
| A | 共享 Policy Baseline | 已完成 |
| C | Weighted08 | 待测 |
| D2 | 几何邻域 Critic + Weighted08 | 已完成 |

## 当前结果

| 方法 | success_rate | collision_rate | full_success_rate |
| --- | ---: | ---: | ---: |
| A 共享 Policy Baseline | 0.993 | 0.004 | 0.983 |
| D2 几何邻域 Critic + Weighted08 | 0.996 | 0.001 | 0.987 |
