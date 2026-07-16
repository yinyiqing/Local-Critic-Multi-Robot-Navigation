# D2. 三车几何邻域 Critic + Weighted08

本目录归档三车主线实验 D2，也是当前表现较好的版本。

## 方法定义

- reward：Weighted08，即 `0.8 * own reward + 0.2 * distance-weighted neighbor reward`
- actor 执行输入：本车 24 维 observation
- 执行阶段：无通信，不读取邻居信息
- critic 训练输入：本车 observation、本车 action、邻居几何、mask
- 与 D 的区别：去掉邻居动作，只保留几何邻域信息
- warm-start：`TD3_velodyne_multi_v4`

## 当前结论

D2 在 20 epoch 扩展训练后更新 best，并在 300 episodes 测试中取得当前最高三车全成功率。

这说明对当前任务而言，critic 使用更干净的几何邻域 context 比同时加入邻居动作更稳定。

## 核心文件

- `三车几何邻域Critic加Weighted08/test_multi_local_critic_geo_3_best_300episodes_summary.md`
- `三车几何邻域Critic加Weighted08/test_multi_local_critic_geo_3_best_300episodes_clean.log`
- `三车几何邻域Critic加Weighted08/train_multi_local_critic_geo_3_10epoch.raw.log`
- `三车几何邻域Critic加Weighted08/train_multi_local_critic_geo_3_extended20.raw.log`
