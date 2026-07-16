# 08 5A 人工密集诊断

## 目的

用当前主线 5A 模型测试五车人工密集场景，确认它是否已经具备处理强交互 case 的能力。

## 模型

- `TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best`
- 这是当前五车共享 policy 主线模型。

## 测试

- 场景：`stage2_dense`
- 机器人数量：5
- episode：120
- case 数量：4，每个 case 约 30 次
- 日志：`logs/test/test_multi_curriculum_stage2_dense_TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best_detached_20260609_124550.log`

## 结果

整体：

- success：240 / 600 = 0.400
- collision：370 / 600 = 0.617
- unresolved：3 / 600 = 0.005
- full success：9 / 120 = 0.075
- timeout episode：3 / 120 = 0.025

分 case：

| case | success | collision | full success | 结论 |
| --- | ---: | ---: | ---: | --- |
| `cross_center_5` | 0.020 | 0.973 | 0.000 | 几乎完全失败 |
| `clustered_starts_spread_goals` | 0.213 | 0.787 | 0.000 | 严重失败 |
| `wall_adjacent_crossing` | 0.607 | 0.380 | 0.133 | 中等失败 |
| `spread_starts_clustered_goals` | 0.760 | 0.327 | 0.167 | 相对可处理 |

## 结论

当前 5A 模型在五车随机标准测试上可作为主线继续使用，但还没有掌握人工密集强交互。问题集中在中心交叉和密集起点扩散这两类 case，主要表现为早期碰撞，而不是超时或到不了目标。

下一步不建议直接硬训完整 `stage2_dense`。更稳的方向是做一个五车第二课程的渐进版：先放松 `cross_center_5` 和 `clustered_starts_spread_goals` 的初始间距、目标冲突强度或参与车辆数，再逐步恢复到完整密集场景。
