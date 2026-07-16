# E. 五车纯几何邻域 Critic

本目录归档五车规模下的纯几何邻域 Critic 实验。

## 方法定义

- reward：普通 individual reward
- actor 执行输入：本车 24 维 observation
- critic 训练输入：本车 observation、本车 action、邻居几何、mask
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`

## 当前结论

纯几何邻域 Critic 的整体表现接近 baseline，但没有超过 baseline。相比 Weighted08 和 D2，它的 full_success_rate 明显更高，说明五车 D2 的主要下降更可能来自 Weighted08 的 reward 设计，而不是几何邻域 critic 单独导致。

## 核心文件

- `五车纯几何邻域Critic/train_multi_local_critic_geo_individual_5_detached_20260527_203955.log`
- `五车纯几何邻域Critic/test_multi_local_critic_geo_individual_5_best_detached_20260528_092253.raw.log`
- `五车纯几何邻域Critic/test_multi_local_critic_geo_individual_5_best_300episodes_clean.log`
- `五车纯几何邻域Critic/test_multi_local_critic_geo_individual_5_best_300episodes_summary.md`
