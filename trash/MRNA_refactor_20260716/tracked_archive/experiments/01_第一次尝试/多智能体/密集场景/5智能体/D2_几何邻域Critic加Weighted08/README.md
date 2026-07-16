# D2. 五车密集场景几何邻域 Critic + Weighted08

本目录归档五车 dense case 的几何邻域 Critic + Weighted08 测试结果。

## 方法定义

- 训练模型：`TD3_velodyne_multi_v4_local_critic_geo_5`
- 测试模型：`TD3_velodyne_multi_v4_local_critic_geo_5_best`
- 测试场景：`dense`
- 机器人数量：5
- 测试集数：300 episodes
- actor 执行输入：本车 24 维 observation
- critic 训练输入：本车 observation、本车 action、邻居几何、mask

## 当前结论

五车 dense case 中，D2 的碰撞率低于 baseline，但 success_rate 和 full_success_rate 均低于 baseline。

这说明 D2 在五车 dense case 中仍表现为更保守的策略：碰撞更少，但完成效率和全体完成率下降。

## 核心文件

- `五车密集几何邻域Critic加Weighted08/test_multi_dense_local_critic_geo_5_best_detached_20260526_150725.raw.log`
- `五车密集几何邻域Critic加Weighted08/test_multi_dense_local_critic_geo_5_best_300episodes_clean.log`
- `五车密集几何邻域Critic加Weighted08/test_multi_dense_local_critic_geo_5_best_300episodes_summary.md`
