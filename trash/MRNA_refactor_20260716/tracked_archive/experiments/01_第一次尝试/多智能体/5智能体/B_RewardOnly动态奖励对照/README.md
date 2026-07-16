# B. 五车 RewardOnly 动态奖励对照

本目录归档五车规模下的 RewardOnly 动态奖励对照实验。

## 方法定义

- reward：训练阶段使用可见邻居 reward 平均
- actor 执行输入：本车 24 维 observation
- critic：普通 TD3 critic，不额外输入邻居信息
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`

## 当前结论

RewardOnly 在五车标准场景中的个体成功率略高于 baseline，碰撞率低于 baseline，但 full_success_rate 略低。

该结果说明单独引入动态 reward 并没有明显破坏五车策略，也没有稳定提升全体完成率。后续需要结合 Weighted08 和 D2 判断性能变化主要来自 reward mixing 还是 critic 结构。

## 核心文件

- `五车RewardOnly/train_multi_reward_only_5_detached_20260526_230021.log`
- `五车RewardOnly/test_multi_reward_only_5_best_detached_20260527_084356.raw.log`
- `五车RewardOnly/test_multi_reward_only_5_best_300episodes_clean.log`
- `五车RewardOnly/test_multi_reward_only_5_best_300episodes_summary.md`
