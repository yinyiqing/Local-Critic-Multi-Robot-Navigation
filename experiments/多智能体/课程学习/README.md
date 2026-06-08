# 多机器人课程学习实验总账

本目录归档课程学习相关实验。每个实验目录包含目的、配置、关键结果和日志去向；`cases/` 只放可复用的 case 定义。

这里按“课程”理解，而不是按每个脚本参数理解。第一课程是单车局部导航；第二课程是多车主线回接；第三课程才进入多车人工密集交互。

## 当前主线

| 课程目录 | 状态 | 作用 | 当前口径 |
| --- | --- | --- | --- |
| `第一课程_单车局部导航/` | completed | 先把单车局部导航补稳 | 保守基准用 `stage1g best`，hard-suite 候选用 `stage1i best` |
| `第二课程_多车主线回接/` | completed | 把课程 actor 接回 2A/2D/3A/3D2 主线 | 课程 3D2 best 普通三车 full success `0.830`，优势很小 |
| `第三课程_多车密集交互/` | pending | 手工密集交互、过渡集、随机多车 | 等第二课程 3D2 节点明确后启动 |
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

第二课程不是继续让单车单独背 case，也不是直接上人工密集场景，而是把第一课程的局部导航能力接回原来的多车主线。

当前主线节点是：

- 2A：共享 policy。
- 2D：原始局部 critic。
- 3A：共享 policy。
- 3D：原始局部 critic。
- 3D2：几何邻域 critic。

第三课程才处理人工设计的密集交互 case。

## 日志归档规则

- 每个实验自己的日志放在该实验目录下的 `logs/` 子目录。
- `logs/train/`：训练日志。
- `logs/test/`：有效测试日志。
- `logs/failed/`：启动失败或无效测试。
- `logs/superseded/`：已复盘但不作为主线模型的训练。
- 根目录 `/logs/` 只保留当前运行日志的软链接，方便实时查看。
- 早期已清理 raw log 的目录必须在本 README 和各自 README 中说明“仅保留摘要”，避免误判为实验缺失。
