# C. 五车 Weighted08 距离加权奖励对照

本目录归档五车规模下的 Weighted08 距离加权奖励对照实验。

## 方法定义

- reward：`0.8 * own reward + 0.2 * distance-weighted neighbor reward`
- actor 执行输入：本车 24 维 observation
- critic：普通 TD3 critic，不额外输入邻居信息
- 执行阶段：无通信，不读取邻居信息
- warm-start：`TD3_velodyne_multi_v4`

## 当前结论

Weighted08 在五车标准场景中的碰撞率低于 baseline，但 success_rate 和 full_success_rate 明显下降，avg_env_steps 明显增加。

这说明 Weighted08 在五车规模下会让策略更保守、更慢。结合 D2 结果看，五车 D2 的下降并不只是几何邻域 critic 的问题，Weighted08 本身已经带来明显的完成效率损失。

## 核心文件

- `五车Weighted08/train_multi_weighted08_5_detached_20260527_103842.log`
- `五车Weighted08/test_multi_weighted08_5_best_detached_20260527_164757.raw.log`
- `五车Weighted08/test_multi_weighted08_5_best_300episodes_clean.log`
- `五车Weighted08/test_multi_weighted08_5_best_300episodes_summary.md`
