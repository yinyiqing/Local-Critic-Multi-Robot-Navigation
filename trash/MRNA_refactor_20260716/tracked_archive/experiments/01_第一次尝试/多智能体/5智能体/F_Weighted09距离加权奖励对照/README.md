# F. 五车 Weighted09 距离加权奖励对照

本目录归档五车规模下的 Weighted09 距离加权奖励对照实验。

## 方法定义

- reward：`0.9 * own reward + 0.1 * distance-weighted neighbor reward`
- actor 执行输入：本车 24 维 observation
- critic：普通 TD3 critic，不额外输入邻居信息
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`

## 当前结论

Weighted09 相比 Weighted08 明显缓解了过度保守的问题：full_success_rate、success_rate 和 avg_env_steps 都更接近 baseline。

但 Weighted09 仍未超过 baseline。它的主要价值是说明五车场景下邻居 reward 权重不宜过高，`0.1` 比 `0.2` 更稳，但目前还不能形成明确优势。

## 核心文件

- `五车Weighted09/train_multi_weighted09_5_detached_20260528_153053.log`
- `五车Weighted09/test_multi_weighted09_5_best_detached_20260528_221626.raw.log`
- `五车Weighted09/test_multi_weighted09_5_best_300episodes_clean.log`
- `五车Weighted09/test_multi_weighted09_5_best_300episodes_summary.md`
