# D2. 五车几何邻域 Critic + Weighted08

本目录归档五车规模下的几何邻域 Critic + Weighted08 实验。

## 方法定义

- reward：Weighted08，即 `0.8 * own reward + 0.2 * distance-weighted neighbor reward`
- actor 执行输入：本车 24 维 observation
- 执行阶段：无通信，不读取邻居信息
- critic 训练输入：本车 observation、本车 action、邻居几何、mask
- 邻居 context：`relative_x, relative_y, distance, bearing, mask`
- warm-start：`TD3_velodyne_multi_v4`

## 当前结论

五车 D2 能完成 300 episodes 测试，但整体任务完成效果低于五车共享 Policy Baseline。

与 baseline 相比，D2 的碰撞率略低，但个体成功率和全成功率更低，说明几何邻域 critic 在五车标准场景中没有直接带来整体收益。这个结果提示后续需要重点检查五车交互复杂度、训练稳定性、邻域阈值和密集场景表现。

## 核心文件

- `五车几何邻域Critic加Weighted08/train_multi_local_critic_geo_5_detached_20260525_214438.log`
- `五车几何邻域Critic加Weighted08/test_multi_local_critic_geo_5_best_detached_20260526_091118.raw.log`
- `五车几何邻域Critic加Weighted08/test_multi_local_critic_geo_5_best_300episodes_clean.log`
- `五车几何邻域Critic加Weighted08/test_multi_local_critic_geo_5_best_300episodes_summary.md`
