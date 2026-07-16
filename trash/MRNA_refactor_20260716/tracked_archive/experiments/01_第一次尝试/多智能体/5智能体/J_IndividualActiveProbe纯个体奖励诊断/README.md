# J. 五车 Individual Active Probe 纯个体奖励诊断

本目录归档五车规模下的 Individual Active Probe 诊断实验。

## 方法定义

- reward：等价于纯 individual reward
- 实现方式：走 `interaction_only` 动态奖励通道，但 `interaction_close_penalty=0.0`、`interaction_stagnation_penalty=0.0`
- 目的：保留 active-neighbor exposure 诊断日志，同时排除局部 interaction penalty 对 reward 的影响
- actor 执行输入：本车 24 维 observation
- critic：普通 TD3 critic，不额外输入邻居信息
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`
- best 选择标准：`full_success_rate`
- 训练预算：8 epochs，eval 每次 30 episodes

## 训练内评估

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate | avg_reward | avg_env_steps | avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.673 | 0.240 | 0.087 | 0.067 | 0.400 | 57.251 | 167.0 | 0.609 |
| 2 | 0.867 | 0.073 | 0.067 | 0.500 | 0.267 | 103.451 | 100.6 | 0.338 |
| 3 | 0.907 | 0.053 | 0.040 | 0.633 | 0.167 | 111.906 | 69.8 | 0.239 |
| 4 | 0.880 | 0.093 | 0.027 | 0.500 | 0.133 | 102.664 | 72.4 | 0.272 |
| 5 | 0.847 | 0.133 | 0.020 | 0.500 | 0.100 | 97.790 | 57.6 | 0.345 |
| 6 | 0.880 | 0.073 | 0.047 | 0.567 | 0.233 | 104.458 | 99.5 | 0.332 |
| 7 | 0.887 | 0.073 | 0.040 | 0.467 | 0.200 | 105.518 | 100.7 | 0.287 |
| 8 | 0.867 | 0.067 | 0.067 | 0.567 | 0.333 | 104.076 | 142.2 | 0.376 |

Best checkpoint 出现在 epoch 3：`full_success_rate=0.633`，`success_rate=0.907`，`collision_rate=0.053`，`timeout_episode_rate=0.167`。

## 交互信号诊断

训练共完成 319 个 episode。episode 级统计均值：

- `active_neighbor_step_rate=0.6185`
- `mean_active_neighbors_step=1.2885`
- `interaction_reward=0.0000`
- `abs_interaction_reward=0.0000`

这说明 J 组确实是纯 individual reward，同时仍然保留了 active-neighbor exposure 观测。

## 当前结论

J 的 300 episodes best 测试结果为 `success_rate=0.869`、`collision_rate=0.087`、`full_success_rate=0.537`、`timeout_episode_rate=0.197`。它接近 baseline/H 的 `full_success_rate=0.540`，略低于 I 组 `0.553`。

这说明 I 组相对 baseline/H 的小幅提升不一定来自局部 interaction penalty 本身，也可能来自短训练、early stopping 或重训随机性。J 组纯 individual reward 仍能达到同一量级表现，削弱了“局部 interaction penalty 已经稳定带来协同能力”的判断。

J 的 timeout 结构进一步支持当前 deadlock 诊断：59 个 timeout episode 中，35 个已经有 4/5 机器人成功，19 个已经有 3/5 机器人成功，且 52 个只剩 1 个 unresolved agent。这说明主要长尾不是五车整体失败，而是多数机器人完成并停住后，最后一两辆进入静止/小范围摆动/局部死锁。

## 核心文件

- `五车IndividualActiveProbe/train_multi_individual_active_probe_5_detached_20260601_091906.log`
- `五车IndividualActiveProbe/test_multi_individual_active_probe_5_best_detached_20260601_145111.raw.log.gz`
- `五车IndividualActiveProbe/test_multi_individual_active_probe_5_best_300episodes_clean.log`
- `五车IndividualActiveProbe/test_multi_individual_active_probe_5_best_300episodes.npy`
- `五车IndividualActiveProbe/test_multi_individual_active_probe_5_best_300episodes_summary.md`
