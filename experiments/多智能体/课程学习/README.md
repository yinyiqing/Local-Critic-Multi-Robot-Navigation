# 多机器人课程学习实验总账

本目录归档课程学习相关实验。每个实验目录包含目的、配置、关键结果和归档日志；`cases/` 只放可复用的 case 定义。

## 当前主线

| 阶段 | 状态 | 作用 | 主要模型 |
| --- | --- | --- | --- |
| `stage1_single_local_navigation/` | completed | 单车局部导航起点 | `TD3_velodyne_multi_v4_curriculum_stage1_single_best` |
| `stage1b_near_goal_sidewall_diagnostic/` | diagnostic | 发现近目标和侧墙仍不稳 | `TD3_velodyne_multi_v4_curriculum_stage1_single_best` |
| `stage1e_single_rescue/` | completed | 修复近目标、贴墙目标和墙边基础缺陷 | `TD3_velodyne_multi_v4_curriculum_stage1e_single_rescue_from_stage1_single_best` |
| `stage1f_wall_parallel_rescue/` | completed | 补墙边平行通行 | `TD3_velodyne_multi_v4_curriculum_stage1f_wall_parallel_rescue_from_stage1e_best` |
| `stage1g_collision_guard/` | current baseline | 当前最可信单车候选 | `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best` |
| `stage1h_separated_reverse_guard/` | superseded / test suite | 训练效果不佳，但保留为难例评估集 | `stage1h` best 不作为主模型 |
| `stage1i_yaw_reverse_collision_guard/` | active | 正在压缩 yaw/reverse collision 尾巴 | `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g` |

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

## 当前判断

当前不应进入多车密集训练。`stage1g` 已解决大部分墙边和近目标问题，但在 `stage1h` 难例集上仍有 collision tail。`stage1i` 正在从 `stage1g` best warm-start，目标是压低 `wall_separated_north_yaw_in/out` 和 `wall_parallel_reverse_safe/clear` 的碰撞率。

下一步只比较 best checkpoint：`stage1g best`、`stage1h best`、`stage1i best` 在相同难例集和综合单车集上的结果。
