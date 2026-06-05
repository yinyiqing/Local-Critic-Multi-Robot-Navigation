# 多机器人课程学习实验总账

本目录归档课程学习相关实验。每个实验目录包含目的、配置、关键结果和日志去向；`cases/` 只放可复用的 case 定义。

这里的口径是“课程学习线总账”，不是全项目日志池。旧的五车标准场景、密集场景和容量验证日志已经放在各自实验目录下，不混入本目录。

## 当前主线

| 阶段 | 状态 | 作用 | 主要模型 |
| --- | --- | --- | --- |
| `stage1_single_local_navigation/` | completed | 单车局部导航起点 | `TD3_velodyne_multi_v4_curriculum_stage1_single_best` |
| `stage1b_near_goal_sidewall_diagnostic/` | diagnostic | 发现近目标和侧墙仍不稳 | `TD3_velodyne_multi_v4_curriculum_stage1_single_best` |
| `stage1e_single_rescue/` | completed | 修复近目标、贴墙目标和墙边基础缺陷 | `TD3_velodyne_multi_v4_curriculum_stage1e_single_rescue_from_stage1_single_best` |
| `stage1f_wall_parallel_rescue/` | completed | 补墙边平行通行 | `TD3_velodyne_multi_v4_curriculum_stage1f_wall_parallel_rescue_from_stage1e_best` |
| `stage1g_collision_guard/` | conservative baseline | 综合单车集最稳候选 | `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best` |
| `stage1h_separated_reverse_guard/` | superseded / test suite | 训练效果不佳，但保留为难例评估集 | `stage1h` best 不作为主模型 |
| `stage1i_yaw_reverse_collision_guard/` | completed / candidate | hard suite 更强，但综合集略低于 stage1g | `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best` |

## 完整实验索引

| 目录 | 类型 | raw log 状态 | 说明 |
| --- | --- | --- | --- |
| `stage1_single_local_navigation/` | completed | 仅保留摘要 | 第一版单车局部导航课程，best 在 epoch 4；后续发现覆盖不够。 |
| `stage1b_near_goal_sidewall_diagnostic/` | diagnostic | 仅保留摘要 | 诊断出 `wall_parallel_close_pass` 和 `goal_adjacent_wall_capture` 不稳。 |
| `stage1_single_to_5_standard_transfer_diagnostic/` | diagnostic | 仅保留摘要 | 单车 best 直接迁移到五车标准场景会出现摆动、超时和低 full success。 |
| `stage2_three_dense_intermediate_diagnostic/` | paused diagnostic | 仅保留摘要 | 三车密集训练暴露底层局部导航仍不稳，因此暂停。 |
| `aborted/stage2_dense_too_hard_20260602/` | aborted | 仅保留摘要 | 五车 dense 过早，epoch 1 已显示难度过高。 |
| `stage1e_single_rescue/` | completed | `logs/` 已归档 | 修复近目标、目标贴墙和基础墙边缺陷。 |
| `stage1f_wall_parallel_rescue/` | completed | `logs/` 已归档 | 继续补墙边平行通行和 yaw-in。 |
| `stage1g_collision_guard/` | conservative baseline | `logs/` 已归档 | 综合单车集 `117/120`，targeted test 为 `120/120`。 |
| `stage1h_separated_reverse_guard/` | superseded / test suite | `logs/` 已归档 | 训练不采用，但保留为 hard suite。 |
| `stage1i_yaw_reverse_collision_guard/` | completed / candidate | `logs/` 已归档 | hard suite `112/120`，综合单车集 `115/120`。 |

## 暂停或诊断项

| 目录 | 状态 | 说明 |
| --- | --- | --- |
| `stage1_single_to_5_standard_transfer_diagnostic/` | diagnostic | 说明单车 best 直接复制到五车会出现摆动和超时 |
| `stage2_three_dense_intermediate_diagnostic/` | paused | 三车密集课程暴露底层局部导航仍不稳，暂停推进 |
| `aborted/stage2_dense_too_hard_20260602/` | aborted | 五车密集课程过早，先回到单车阶段 |

## 日志归档规则

- 每个实验自己的日志放在该实验目录下的 `logs/` 子目录。
- `logs/train/`：训练日志。
- `logs/test/`：有效测试日志。
- `logs/failed/`：启动失败或无效测试。
- `logs/superseded/`：已复盘但不作为主线模型的训练。
- 根目录 `/logs/` 只保留当前运行日志的软链接，方便实时查看。
- 早期已清理 raw log 的目录必须在本 README 和各自 README 中说明“仅保留摘要”，避免误判为实验缺失。

## 当前判断

当前不应进入多车密集训练。`stage1g` 已解决大部分墙边和近目标问题，但在 `stage1h` 难例集上仍有 collision tail。`stage1i` 从 `stage1g` best warm-start 后，把 hard suite 从 `105/120` 提到 `112/120`，但综合单车集从 stage1g 的 `117/120` 降到 `115/120`。

因此当前有两个可选基准：保守推进用 `stage1g best`；若优先压 hard-suite collision tail，可用 `stage1i best`，但需要接受综合集略微回落。
