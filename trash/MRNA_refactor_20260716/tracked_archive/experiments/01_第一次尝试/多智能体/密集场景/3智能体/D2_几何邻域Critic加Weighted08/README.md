# D2 几何邻域 Critic + Weighted08

本目录归档 3 智能体密集场景下的几何邻域 Critic + Weighted08 测试结果。

## 方法口径

- 模型：`TD3_velodyne_multi_v4_local_critic_geo_3_best`
- 场景：`dense`
- 机器人数量：3
- 每辆机器人有独立目标
- critic 训练阶段使用局部邻居几何信息
- 执行阶段 actor 输入不变，仍只使用本车 observation
- 测试规模：300 episodes

## 结果目录

- `三车密集几何邻域Critic加Weighted08/`

