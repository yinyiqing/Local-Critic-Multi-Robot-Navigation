# M. 五车 Individual Anti-Stagnation 停滞惩罚诊断

本目录归档五车规模下的 Individual Anti-Stagnation 诊断实验。

## 方法定义

- reward：以 J 组纯 individual reward 为基础，训练阶段额外加入本车停滞惩罚
- 停滞条件：active、未完成、未碰撞、线速度低、单步 progress 很小、且不是贴近障碍碰撞边界
- actor 执行输入：本车 24 维 observation
- critic：普通 TD3 critic，不额外输入邻居信息
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`
- best 选择标准：`full_success_rate`
- 训练预算：8 epochs，eval 每次 30 episodes
- 测试阶段：关闭 anti-stagnation reward，保持 individual reward 统计口径

## 训练内评估

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate | avg_reward | avg_env_steps | avg_final_distance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.720 | 0.260 | 0.033 | 0.133 | 0.167 | 71.525 | 92.7 | 0.486 |
| 2 | 0.900 | 0.073 | 0.027 | 0.567 | 0.133 | 109.414 | 59.8 | 0.256 |
| 3 | 0.867 | 0.067 | 0.073 | 0.533 | 0.333 | 102.454 | 119.8 | 0.339 |
| 4 | 0.787 | 0.167 | 0.047 | 0.333 | 0.200 | 84.549 | 91.4 | 0.444 |
| 5 | 0.887 | 0.080 | 0.033 | 0.500 | 0.167 | 105.073 | 79.0 | 0.290 |
| 6 | 0.860 | 0.080 | 0.060 | 0.433 | 0.267 | 103.234 | 115.3 | 0.307 |
| 7 | 0.873 | 0.053 | 0.080 | 0.467 | 0.400 | 102.764 | 135.1 | 0.324 |
| 8 | 0.853 | 0.067 | 0.080 | 0.367 | 0.367 | 99.347 | 140.6 | 0.362 |

Best checkpoint 出现在 epoch 2：`full_success_rate=0.567`，`success_rate=0.900`，`collision_rate=0.073`，`timeout_episode_rate=0.133`。

## 当前结论

M 的 300 episodes best 测试结果为 `success_rate=0.864`、`collision_rate=0.125`、`full_success_rate=0.530`、`timeout_episode_rate=0.073`。与 J 组 `success_rate=0.869`、`collision_rate=0.087`、`full_success_rate=0.537`、`timeout_episode_rate=0.197` 相比，M 降低了 timeout，但没有提升 full success，且 collision 明显升高。

这说明简单的低速/低 progress 停滞惩罚不是五车主线解法。它可能把一部分长尾 timeout 转换成更快结束的碰撞或失败 episode，但没有解决 RViz 中观察到的两类核心局部缺陷：目标隔墙时的局部最小值，以及接近目标后擦身/绕圈而不进入成功半径。

因此，anti-stagnation 分支应停止继续调参。下一步应转向更直接的诊断和修复：近目标捕获失败、墙后目标局部最小值，而不是继续堆 reward shaping。

## 核心文件

- `五车IndividualAntiStagnation/train_multi_individual_antistagnation_5_detached_20260601_194529.log`
- `五车IndividualAntiStagnation/test_multi_individual_antistagnation_5_best_detached_20260601_233854.partial.raw.log.gz`
- `五车IndividualAntiStagnation/test_multi_individual_antistagnation_5_best_detached_20260601_234131.resume.raw.log.gz`
- `五车IndividualAntiStagnation/test_multi_individual_antistagnation_5_best_300episodes_clean.log`
- `五车IndividualAntiStagnation/test_multi_individual_antistagnation_5_best_300episodes.npy`
- `五车IndividualAntiStagnation/test_multi_individual_antistagnation_5_best_300episodes_summary.md`
