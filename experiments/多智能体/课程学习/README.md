# 多机器人课程学习实验总账

本目录归档课程学习相关实验。每个实验目录包含目的、配置、关键结果和日志去向；`cases/` 只放可复用的 case 定义。

这里按“课程”理解，而不是按每个脚本参数理解。第一课程是单车局部导航这一门课，里面的 `stage1e/f/g/i` 是补课、修补和对照；第二课程才进入多车人工密集交互。

## 当前主线

| 课程目录 | 状态 | 作用 | 当前口径 |
| --- | --- | --- | --- |
| `第一课程_单车局部导航/` | completed | 先把单车局部导航补稳 | 保守基准用 `stage1g best`，hard-suite 候选用 `stage1i best` |
| `第二课程_多车人工密集交互/` | active | 人工设计 3 车密集、交错、靠近 case | `stage2a_manual_dense_crossing` 从 `stage1g best` warm-start |
| `诊断记录/` | archived | 记录为什么要补某些 case | 只保留复盘摘要 |
| `废弃分支/` | archived | 记录过早或过难的分支 | 只保留复盘摘要 |

## 第一课程结论

第一课程已经够用，可以停止继续加 `stage1j/k`。目前两份可用模型：

| 模型 | 角色 | 已知结果 |
| --- | --- | --- |
| `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best` | 保守基准 | 综合单车集 `117/120`，hard suite `105/120` |
| `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best` | 难例候选 | hard suite `112/120`，综合单车集 `115/120` |

下一步先用 `stage1g best` 推第二课程，因为它综合单车集最稳；`stage1i best` 留作对照。

## 第二课程计划

第二课程不是继续让单车单独背 case，而是把第一课程的局部导航能力带进多车场景。这里手工设计 3 车起点和目标点，故意制造中心交叉、近距离会车、起点聚集、目标聚集、墙边会车和窄路超车。

切换时不直接继承第一课程末期的极低探索状态。当前配置是：

- agents: 3
- actor lr / critic lr: `0.00005`
- exploration noise: `0.055`
- exploration min: `0.018`
- max epochs: 8
- eval episodes: 48
- local-navigation reward: on
- wall-clearance reward: off by default

## 日志归档规则

- 每个实验自己的日志放在该实验目录下的 `logs/` 子目录。
- `logs/train/`：训练日志。
- `logs/test/`：有效测试日志。
- `logs/failed/`：启动失败或无效测试。
- `logs/superseded/`：已复盘但不作为主线模型的训练。
- 根目录 `/logs/` 只保留当前运行日志的软链接，方便实时查看。
- 早期已清理 raw log 的目录必须在本 README 和各自 README 中说明“仅保留摘要”，避免误判为实验缺失。
