# A. 五车密集场景共享 Policy Baseline

本目录归档五车 dense case 的共享 Policy Baseline 测试结果。

## 方法定义

- 训练模型：`TD3_velodyne_multi_v4_shared_policy_5`
- 测试模型：`TD3_velodyne_multi_v4_shared_policy_5_best`
- 测试场景：`dense`
- 机器人数量：5
- 测试集数：300 episodes

## 当前结论

五车 dense case 中 baseline 表现很强，个体成功率和全成功率都明显高于五车标准场景。

这说明当前 dense 设置更偏向短程局部交互验证。虽然机器人处在更小空间内，但目标距离也更短，因此整体任务难度不一定高于标准场景。

## 核心文件

- `五车密集共享PolicyBaseline/test_multi_dense_baseline_5_best_detached_20260526_134022.raw.log`
- `五车密集共享PolicyBaseline/test_multi_dense_baseline_5_best_300episodes_clean.log`
- `五车密集共享PolicyBaseline/test_multi_dense_baseline_5_best_300episodes_summary.md`
