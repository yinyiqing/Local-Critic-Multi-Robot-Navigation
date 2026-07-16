# I. 五车 InteractionOnly Active 局部交互奖励对照

本目录归档五车规模下的 InteractionOnly active-neighbor 诊断实验。

## 方法定义

- reward：本车 individual reward + active-neighbor 局部交互惩罚
- interaction-only：不再平均邻居完整 reward，只在本车雷达/FOV 内存在 active 邻居时加入小幅局部项
- 交互项：近距离压力惩罚 + 近邻场景下的低进展惩罚
- active-neighbor：训练阶段只把仍在活动的机器人纳入可见邻居集合
- actor 执行输入：本车 24 维 observation
- critic：普通 TD3 critic，不额外输入邻居信息
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`
- best 选择标准：`full_success_rate`
- 训练预算：8 epochs，eval 每次 30 episodes

## 训练内评估

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate | avg_reward | avg_env_steps | avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.733 | 0.073 | 0.193 | 0.233 | 0.600 | 84.267 | 208.9 | 0.420 |
| 2 | 0.840 | 0.093 | 0.067 | 0.433 | 0.267 | 98.307 | 104.4 | 0.345 |
| 3 | 0.853 | 0.107 | 0.040 | 0.433 | 0.200 | 100.026 | 81.2 | 0.308 |
| 4 | 0.907 | 0.080 | 0.020 | 0.667 | 0.100 | 110.511 | 53.5 | 0.274 |
| 5 | 0.900 | 0.040 | 0.060 | 0.567 | 0.267 | 109.774 | 116.8 | 0.269 |
| 6 | 0.873 | 0.080 | 0.047 | 0.533 | 0.200 | 105.335 | 92.9 | 0.292 |
| 7 | 0.900 | 0.033 | 0.067 | 0.533 | 0.333 | 109.985 | 145.3 | 0.288 |
| 8 | 0.840 | 0.053 | 0.107 | 0.467 | 0.433 | 98.465 | 164.5 | 0.356 |

Best checkpoint 出现在 epoch 4：`full_success_rate=0.667`，`success_rate=0.907`，`collision_rate=0.080`，`timeout_episode_rate=0.100`。

## 交互信号诊断

训练共完成 279 个 episode。episode 级统计均值：

- `active_neighbor_step_rate=0.6275`
- `mean_active_neighbors_step=1.2827`
- `interaction_reward=-0.0039`
- `abs_interaction_reward=0.0039`

这说明五车训练中 active 邻居暴露并不少，之前只看 episode 末尾的 `coop_agents` 会低估真实交互频率。InteractionOnly 的局部交互项幅度很小，主要作用是去掉邻居完整 reward averaging 的噪声，同时保留一点近距离约束。

## 当前结论

训练内 30 episodes eval 显示，InteractionOnly Active 明显强于 H 的后期表现，并在 epoch 4 达到目前最好的小样本 full-success。它支持一个判断：五车问题不是“没有邻居暴露”，而是旧 cooperative reward 把邻居完整任务 reward 混入本车学习信号，噪声和 credit assignment 负担太大。

300 episodes best checkpoint 测试中，I 的 `full_success_rate=0.553`，略高于 baseline/H 的 `0.540`，是当前最高的五车主线结果；`collision_rate=0.069`，接近 H 的低碰撞表现并明显低于 baseline。但提升幅度很小，且 `timeout_episode_rate=0.230`、`avg_env_steps=95.197`，说明长尾 timeout/deadlock 仍未解决。

因此，I 支持“去掉邻居完整 reward averaging，保留个体任务 reward + 局部交互约束”的方向，但它还不是充分的协同能力突破。下一步应继续处理 timeout 长尾，例如把局部交互项改为更明确的让行/解锁 shaping，或把邻居几何信息开放给 critic 但保持 reward 个体化。

## 核心文件

- `五车InteractionOnlyActive/train_multi_interaction_only_active_5_detached_20260531_144304.log`
- `五车InteractionOnlyActive/test_multi_interaction_only_active_5_best_detached_20260531_215232.raw.log`
- `五车InteractionOnlyActive/test_multi_interaction_only_active_5_best_300episodes_clean.log`
- `五车InteractionOnlyActive/test_multi_interaction_only_active_5_best_300episodes.npy`
- `五车InteractionOnlyActive/test_multi_interaction_only_active_5_best_300episodes_summary.md`
