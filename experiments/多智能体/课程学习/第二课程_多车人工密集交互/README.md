# 第二课程：多车人工密集交互

## 目的

第二课程从第一课程的单车 best warm-start，不再继续单独补墙边 case，而是手工设计多车起点和目标点，故意制造交错、靠近、会车、同区域目标聚集等交互压力。

这一步要回答两个问题：

- 第一课程学到的单车局部能力迁移到多车后会不会重新出现左右摇摆、局部停滞或撞墙。
- 多车失败主要来自交互压力，还是仍然来自单车墙边局部导航缺陷。

## 当前阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| `stage2a_manual_dense_crossing` | ready | 3 车手工密集交互课程，先从 `stage1g best` warm-start。 |

## 训练口径

- agents: 3
- case file: `../cases/stage2a_manual_dense_crossing_cases.json`
- warm-start A: `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best`
- warm-start B: `TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best`
- actor lr: `0.00005`
- critic lr: `0.00005`
- exploration noise: `0.055`
- exploration min: `0.018`
- max epochs: 8
- eval episodes: 48

## 切换原则

从第一课程切到第二课程时，不直接继承末期极低探索状态。第二课程重新设置较小但非零的探索噪声，学习率低于早期单车训练，避免把已经学到的局部导航能力冲坏。

第一组先跑 stage1g best，因为它综合单车集最稳。随后用 stage1i best 做对照，如果它在多车密集交互里明显减少墙边碰撞，再考虑把 stage1i 作为后续候选。

## Case 设计

| case 类型 | 目的 |
| --- | --- |
| 中心交叉 | 制造多车同时穿越同一区域。 |
| 偏移交叉 | 避免只学对称交叉，加入轻微角度偏差。 |
| 起点聚集、目标分散 | 检查密集起步时是否互相碰撞。 |
| 起点分散、目标聚集 | 检查近目标区域是否会堵住或互撞。 |
| 墙边会车 | 检查第一课程的墙边能力在交互压力下是否保持。 |
| 窄通道对向/超车 | 制造近距离避让和让行压力。 |

## 运行命令

保守 warm-start：

```bash
scripts/start_training_detached_multi_curriculum.sh stage2a_manual_dense_crossing
```

stage1i 对照：

```bash
DRL_MULTI_TRAIN_FILE_NAME=TD3_velodyne_multi_v4_curriculum_stage2a_manual_dense_crossing_from_stage1i \
DRL_MULTI_LOAD_MODEL_NAME=TD3_velodyne_multi_v4_curriculum_stage1i_yaw_reverse_collision_guard_from_stage1g_best \
scripts/start_training_detached_multi_curriculum.sh stage2a_manual_dense_crossing
```

## 日志

- `logs/train/`
- `logs/test/`
