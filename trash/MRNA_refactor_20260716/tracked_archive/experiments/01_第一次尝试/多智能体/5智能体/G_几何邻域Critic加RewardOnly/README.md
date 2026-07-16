# G. 五车几何邻域 Critic + RewardOnly

本目录归档五车规模下的几何邻域 Critic + RewardOnly 组合实验。

## 方法定义

- reward：可见邻居 cooperative reward，不使用距离加权 self/neighbor blend
- actor 执行输入：本车 24 维 observation
- critic 训练输入：本车 observation + 本车 action + 邻居几何 + mask
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`

## 当前结论

该组合没有延续 RewardOnly 在五车中的相对优势。相比 B RewardOnly，G 的 success_rate 和 full_success_rate 明显下降，collision_rate 明显升高。

G 的 unresolved_rate 不高，说明主要问题不是超时或保守，而是几何邻域 critic 与 RewardOnly 组合后策略更容易发生碰撞。

## 核心文件

- `五车几何邻域Critic加RewardOnly/train_multi_local_critic_geo_reward_only_5_detached_20260528_235836.log`
- `五车几何邻域Critic加RewardOnly/test_multi_local_critic_geo_reward_only_5_best_detached_20260529_114317.raw.log`
- `五车几何邻域Critic加RewardOnly/test_multi_local_critic_geo_reward_only_5_best_300episodes_clean.log`
- `五车几何邻域Critic加RewardOnly/test_multi_local_critic_geo_reward_only_5_best_300episodes_summary.md`
