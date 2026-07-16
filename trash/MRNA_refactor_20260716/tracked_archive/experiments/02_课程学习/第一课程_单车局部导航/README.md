# 第一课程：单车局部导航

## 目标

第一课程的目标不是解决多车交互，而是先把单车局部导航补稳。前面的测试说明，直接把早期单车模型放进多车场景，会出现墙边左右摇摆、目标贴墙捕获失败、近目标停滞和局部碰撞。因此第一课程把训练拆成一串单车补课 case，先解决这些基础缺陷。

## 做了什么

| 阶段 | 作用 | 结果 |
| --- | --- | --- |
| `stage1_single_local_navigation` | 第一版单车局部导航 | 只保留摘要，后续发现墙边和近目标覆盖不够。 |
| `stage1e_single_rescue` | 补近目标、目标贴墙、可行墙边行驶 | targeted test `103/120`，仍有墙边和平行通行失败。 |
| `stage1f_wall_parallel_rescue` | 补墙边平行通行和 yaw-in | targeted test `109/120`，timeout 明显减少，但 collision tail 仍在。 |
| `stage1g_collision_guard` | 压墙边 collision | targeted test `120/120`；综合单车集 `117/120`；hard suite `105/120`。 |
| `stage1i_yaw_reverse_collision_guard` | 更窄地压 yaw/reverse collision tail | hard suite `112/120`；综合单车集 `115/120`；latest 回退，比较只用 best。 |

`已替代和评估集/stage1h_separated_reverse_guard` 不作为主训练结果使用，它现在的价值是 hard suite，用来检查墙边分离、反向和 yaw 相关难例。

## 当前结论

第一课程已经够用，可以停止继续补单车。当前保留两个模型口径：

| 模型 | 用法 | 理由 |
| --- | --- | --- |
| `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best` | 第二课程保守 warm-start | 综合单车集最高，整体最稳。 |
| `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best` | 第二课程对照候选 | hard suite 更好，但综合单车集略低。 |

不要使用 `stage1i latest`，它在训练末期出现明显回退。

## 怎么理解这个课程

第一课程不是让模型把每个单车 case 都背下来就结束，而是先把会干扰后续多车训练的基础动作缺陷压下去。它的作用类似打地基：墙边能走、目标贴墙能收敛、近目标不乱摆，第二课程才有意义。

下一步进入 `第二课程_多车主线回接`：从 `stage1g best` 起步，先把同一个 policy 接回 2A/2D/3A/3D/3D2 主线。人工密集交互放到第三课程。

## 日志

有效 raw log 已放在各阶段自己的 `logs/` 下，统一索引见上一级 `LOGS.md`。
