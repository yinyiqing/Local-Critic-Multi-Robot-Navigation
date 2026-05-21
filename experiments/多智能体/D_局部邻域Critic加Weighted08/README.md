# D. 三车局部邻域 Critic + Weighted08

本目录归档三车主线实验 D。

## 方法定义

- reward：Weighted08，即 `0.8 * own reward + 0.2 * distance-weighted neighbor reward`
- actor 执行输入：本车 24 维 observation
- 执行阶段：无通信，不读取邻居信息
- critic 训练输入：本车 observation、本车 action、邻居几何、邻居动作、mask
- warm-start：`TD3_velodyne_multi_v4`

## 当前结论

该方法完成 10 epoch 训练和 20 epoch 扩展检查。20 epoch 扩展未更新 best checkpoint，因此正式 300 episodes 结果仍使用 10 epoch 阶段 best。

结果显示，加入邻居动作 context 后没有超过 Weighted08 reward-only critic 对照，说明 critic 看到更多邻居信息不一定更稳。

## 核心文件

- `三车局部邻域Critic加Weighted08/test_multi_local_critic_3_best_300episodes_summary.md`
- `三车局部邻域Critic加Weighted08/test_multi_local_critic_3_best_300episodes_clean.log`
- `三车局部邻域Critic加Weighted08/train_multi_local_critic_3_detached_20260520_140216.log`
- `三车局部邻域Critic加Weighted08/train_multi_local_critic_3_detached_20260521_193351_extended20.log`
