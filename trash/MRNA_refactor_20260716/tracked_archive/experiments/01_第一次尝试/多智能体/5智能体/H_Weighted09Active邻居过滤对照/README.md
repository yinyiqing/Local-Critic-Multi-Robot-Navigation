# H. 五车 Weighted09 Active 邻居过滤对照

本目录归档五车规模下的 Weighted09 active-neighbor 诊断实验。

## 方法定义

- reward：`0.9 * own reward + 0.1 * distance-weighted active-neighbor reward`
- active-neighbor：训练阶段只把仍在活动的机器人纳入 cooperative reward 的可见邻居集合
- actor 执行输入：本车 24 维 observation
- critic：普通 TD3 critic，不额外输入邻居信息
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`
- best 选择标准：`full_success_rate`

## 当前结论

Active-neighbor 过滤后，训练早期出现很强的小样本评估结果：epoch 4 的 20 episodes eval 达到 `full_success_rate=0.750`。但继续训练后明显退化，epoch 20 降到 `full_success_rate=0.200`，说明五车训练存在稳定性和 early-stopping 敏感性问题。

300 episodes 测试中，H 的 `full_success_rate=0.540`，与共享 Policy Baseline 持平；`collision_rate=0.071` 低于 baseline 的 `0.107`，但 `avg_env_steps=92.687`、`timeout_episode_rate=0.233`，完成效率不如 baseline。它没有形成明确优势，但说明 inactive/done 机器人参与 reward averaging 确实是一个会污染训练信号的因素。

## 核心文件

- `五车Weighted09Active/train_multi_weighted09_active_5_detached_20260529_200614.log`
- `五车Weighted09Active/test_multi_weighted09_active_5_best_detached_20260531_120616.raw.log`
- `五车Weighted09Active/test_multi_weighted09_active_5_best_300episodes_clean.log`
- `五车Weighted09Active/test_multi_weighted09_active_5_best_300episodes.npy`
- `五车Weighted09Active/test_multi_weighted09_active_5_best_300episodes_summary.md`
