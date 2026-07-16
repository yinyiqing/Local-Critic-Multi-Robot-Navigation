# Z0. 原始 WarmStart 五车 ZeroShot 对照

本目录归档 `TD3_velodyne_multi_v4` 不经过五车训练，直接在五车 standard 场景测试的诊断对照。

## 方法定义

- 测试模型：`TD3_velodyne_multi_v4`
- 五车训练：无
- actor 执行输入：本车 24 维 observation
- critic：测试阶段不使用
- 执行阶段：无通信，不读取邻居信息

## 当前结论

原始 warm-start 模型在五车场景下明显弱于五车训练后的 A/B/E/F。

这说明五车训练并不是单纯继承原模型能力，确实提升了五车场景适应性。zero-shot 的 avg_env_steps 和 300-step episode 比例明显偏高，说明原模型在五车交互中更容易出现犹豫、绕行慢或局部死锁。

## 核心文件

- `五车ZeroShotWarmStart/test_multi_baseline_5_zero_clean_detached_20260529_153256.raw.log`
- `五车ZeroShotWarmStart/test_multi_baseline_5_zero_clean_300episodes_clean.log`
- `五车ZeroShotWarmStart/test_multi_baseline_5_zero_clean_300episodes_summary.md`
