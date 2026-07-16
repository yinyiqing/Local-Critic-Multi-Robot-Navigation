# 09 5车密集课程失败与修复诊断

## 目的

记录五车密集课程起点选择上的失败尝试，以及 reward 模式修复。这里不是主线模型目录，里面的模型文件已删除，只保留日志作为依据。

## 已归档日志

训练失败：

- `logs/train/train_multi_curriculum_stage2_dense_gentle_detached_20260609_131902.log`
- `logs/train/train_multi_curriculum_stage2_dense_gentle_detached_20260609_154301.log`

reward 修复探针：

- `logs/probe/train_multi_curriculum_stage2_dense_gentle_detached_20260609_151953.log`

桥接课程未提升：

- `logs/bridge/train_multi_curriculum_stage2_dense_bridge_detached_20260609_161654.log`

## 结论

`stage2_dense_gentle` 仍然太难，核心问题是五车同步穿越中心。共享 policy、局部观测、无通信、无优先级时，车辆很容易一起冲向中心，不能稳定自发形成让行规则。

第一次 `stage2_dense_gentle_from_5a` 的 reward 模式是 `average`，不会产生提前避碰惩罚。后来新增 `average_plus_interaction` 后，探针日志确认 `interaction_reward` 已经非零。

即使修复 reward，直接从五车同步中心交叉开始仍不是合适课程起点。因此当前改走 `stage2_dense_bridge`：先训练两车/三车交互，其余车辆走非冲突保留路径，再逐步靠近完整五车密集交叉。

`stage2_dense_bridge` 比同步五车中心交叉更合理，但实际仍未提升。评估结果如下：

| epoch | success | collision | full success | 结论 |
| --- | ---: | ---: | ---: | --- |
| 1 | 0.500 | 0.512 | 0.042 | 起点仍弱 |
| 2 | 0.529 | 0.467 | 0.062 | 最好但仍不够 |
| 3 | 0.342 | 0.617 | 0.021 | 解冻后退化 |

因此当前不再继续五车密集课程试错。保留 5A 普通五车模型作为主线结果，把人工强交互密集 case 记录为未解决边界。

## 清理

以下失败或探针模型已删除，避免误用：

- `TD3_velodyne_multi_v4_curriculum_stage2_dense_gentle_from_5a*`
- `TD3_velodyne_multi_v4_curriculum_stage2_dense_gentle_avgint_from_5a*`
- `TD3_velodyne_multi_v4_curriculum_stage2_dense_gentle_reward_probe_from_5a*`
- `TD3_velodyne_multi_v4_curriculum_stage2_dense_bridge_avgint_from_5a*`

当前主线仍回到：

- `TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best`
