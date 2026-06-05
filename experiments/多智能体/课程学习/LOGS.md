# 课程学习日志索引

本文件只索引课程学习线的日志。没有 raw log 的早期实验不是漏归档，而是当时已经清理，只保留 README 中的复盘指标。

## 已归档 Raw Logs

| stage | train | test | failed / superseded |
| --- | --- | --- | --- |
| `stage1e_single_rescue` | `stage1e_single_rescue/logs/train/train_multi_curriculum_stage1e_single_rescue_detached_20260603_225418.log` | `stage1e_single_rescue/logs/test/test_multi_curriculum_stage1e_single_rescue_TD3_velodyne_multi_v4_curriculum_stage1e_single_rescue_from_stage1_single_best_detached_20260604_084520.log`<br>`stage1e_single_rescue/logs/test/test_multi_curriculum_stage1e_single_rescue_TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best_detached_20260604_222658.log` | `stage1e_single_rescue/logs/failed/test_multi_curriculum_stage1e_single_rescue_TD3_velodyne_multi_v4_curriculum_stage1e_single_rescue_from_stage1_single_best_detached_20260604_083525.log` |
| `stage1f_wall_parallel_rescue` | `stage1f_wall_parallel_rescue/logs/train/train_multi_curriculum_stage1f_wall_parallel_rescue_detached_20260604_094504.log` | `stage1f_wall_parallel_rescue/logs/test/test_multi_curriculum_stage1f_wall_parallel_rescue_TD3_velodyne_multi_v4_curriculum_stage1f_wall_parallel_rescue_from_stage1e_best_detached_20260604_145439.log` | - |
| `stage1g_collision_guard` | `stage1g_collision_guard/logs/train/train_multi_curriculum_stage1g_collision_guard_detached_20260604_182448.log` | `stage1g_collision_guard/logs/test/test_multi_curriculum_stage1g_collision_guard_TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best_detached_20260604_215320.log` | `stage1g_collision_guard/logs/failed/test_multi_curriculum_stage1g_collision_guard_TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best_detached_20260604_215205.log` |
| `stage1h_separated_reverse_guard` | - | `stage1h_separated_reverse_guard/logs/test/test_multi_curriculum_stage1h_separated_reverse_guard_TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best_detached_20260605_095759.log` | `stage1h_separated_reverse_guard/logs/superseded/train_multi_curriculum_stage1h_separated_reverse_guard_detached_20260604_230204.log` |
| `stage1i_yaw_reverse_collision_guard` | `stage1i_yaw_reverse_collision_guard/logs/train/train_multi_curriculum_stage1i_yaw_reverse_collision_guard_detached_20260605_101704.log` | `stage1i_yaw_reverse_collision_guard/logs/test/test_multi_curriculum_stage1h_separated_reverse_guard_TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best_detached_20260605_120206.log`<br>`stage1i_yaw_reverse_collision_guard/logs/test/test_multi_curriculum_stage1e_single_rescue_TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best_detached_20260605_144056.log` | completed; best is epoch 2, latest regressed |

## Summary-Only Entries

| stage | retained file | reason |
| --- | --- | --- |
| `stage1_single_local_navigation` | `stage1_single_local_navigation/README.md` | raw log and npy were cleaned; summary metrics are retained. |
| `stage1b_near_goal_sidewall_diagnostic` | `stage1b_near_goal_sidewall_diagnostic/README.md` | diagnostic raw outputs were cleaned after extracting case-level results. |
| `stage1_single_to_5_standard_transfer_diagnostic` | `stage1_single_to_5_standard_transfer_diagnostic/README.md` | aborted early after clear failure signal; summary retained. |
| `stage2_three_dense_intermediate_diagnostic` | `stage2_three_dense_intermediate_diagnostic/README.md` | paused branch; summary retained. |
| `aborted/stage2_dense_too_hard_20260602` | `aborted/stage2_dense_too_hard_20260602/README.md` | over-hard branch stopped; summary retained. |
