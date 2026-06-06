# 第二课程：多车人工密集交互

## 目的

第二课程从第一课程的单车 best warm-start，不再继续单独补墙边 case，而是让同一个 policy 开始处理多车交错、靠近、会车、目标区域聚集等交互压力。

这一步要回答两个问题：

- 第一课程学到的单车局部能力迁移到多车后会不会重新出现左右摇摆、局部停滞或撞墙。
- 多车失败主要来自交互压力，还是仍然来自单车墙边局部导航缺陷。

## 当前阶段

第二课程当前只保留一条主线：先确认第一课程能接回 2车A，再从 2车A 接 2车D，稳定后再进入三车密集。

| 主线步骤 | 状态 | 作用 |
| --- | --- | --- |
| 1. `stage1_to_2a_shared` | completed | 第一课程 best 接回 2车A，共享 policy 普通测试优于旧 2车A。 |
| 2. `stage2_2d_local_critic_from_2a_guarded` | active | 从 2车A best 接 2车D；保留 actor、重置 critic、调学习率和探索噪声，先冻结 actor。 |
| 3. 三车密集交互 | pending | 等 2车D 稳定后再推进。 |

旁路记录不作为当前主线继续：

| 记录 | 结论 |
| --- | --- |
| `stage2_2d_local_critic_from_2a` | 直接接 2车D 失败，原因是新 critic 还没稳定就立刻更新 actor。 |
| `stage2_pairwise_diagnostic` | 诊断集，只用于定位双车交互短板。 |
| `stage2_pre_pairwise_warmup` | 有一点效果但不稳定，collision 偏高，不作为主线继续。 |
| `stage2_main_pairwise_repair` | 路线复位前的过早尝试，暂停。 |
| `stage2a_manual_dense_crossing` | 直接上三车太难，暂停。 |

## 主线复位实验结果

`stage1_to_2a_shared` 对应旧 2 车 A 实验，但模型从第一课程 best 接上：

- agents: 2
- scenario: `standard` 2 车主线场景
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best`
- train model: `TD3_velodyne_multi_v4_curriculum_stage2_2a_shared_from_stage1g`
- dynamic reward: off
- distance-weighted reward: off
- local critic: off
- local-navigation reward: off
- wall-clearance reward: off
- actor lr: `0.00008`
- critic lr: `0.00008`
- exploration noise: `0.10`
- exploration min: `0.03`
- max epochs: 12
- eval episodes: 40
- best metric: `success`

训练跑满 12 个 epoch，best checkpoint 在 epoch 2：

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.863 | 0.087 | 0.050 | 0.750 | 0.100 |
| 2 | 0.912 | 0.037 | 0.050 | 0.825 | 0.100 |
| 3 | 0.850 | 0.087 | 0.062 | 0.750 | 0.125 |
| 4 | 0.838 | 0.138 | 0.025 | 0.725 | 0.050 |
| 5 | 0.863 | 0.087 | 0.050 | 0.725 | 0.100 |
| 6 | 0.838 | 0.125 | 0.037 | 0.675 | 0.075 |
| 7 | 0.825 | 0.100 | 0.075 | 0.650 | 0.150 |
| 8 | 0.887 | 0.050 | 0.062 | 0.775 | 0.125 |
| 9 | 0.887 | 0.087 | 0.025 | 0.775 | 0.050 |
| 10 | 0.900 | 0.050 | 0.062 | 0.800 | 0.125 |
| 11 | 0.900 | 0.075 | 0.025 | 0.825 | 0.050 |
| 12 | 0.900 | 0.050 | 0.050 | 0.800 | 0.100 |

结论：

- 第一课程的 `stage1g best` 可以稳定接回 2 车共享 policy 基线，不存在明显迁移断层。
- 这一步说明当前问题不在“从单车到 2 车完全接不上”，而在更强交互机制和更高密度场景下如何降低碰撞、处理让行。
- 下一步应进入 2 车 D 主线机制：共享 policy + 动态 reward + 距离加权 + 局部邻域 critic。优先从 `TD3_velodyne_multi_v4_curriculum_stage2_2a_shared_from_stage1g_best` warm-start。

日志：

- `logs/train/train_multi_stage1_to_2a_shared_detached_20260605_223647.log`

固定测试：

- model: `TD3_velodyne_multi_v4_curriculum_stage2_2a_shared_from_stage1g_best`
- scenario: `standard`
- launchfile: `multi_robot_scenario_multi_2.launch`
- episodes: 300
- agent success: `531 / 600 = 0.885`
- agent collision: `43 / 600 = 0.072`
- agent unresolved: `27 / 600 = 0.045`
- full success: `235 / 300 = 0.783`
- timeout episode: `25 / 300 = 0.083`

这个测试与旧 2 车 A 的普通测试口径一致，不是人工复杂 case；复杂 case 仍看 `stage2_pairwise_diagnostic`。

与旧 2 车 A 的 300 集普通测试对比：

| 模型 | agent success | agent collision | full success | 说明 |
| --- | ---: | ---: | ---: | --- |
| 旧 2 车 A | `475 / 600 = 0.792` | `70 / 600 = 0.117` | `181 / 300 = 0.603` | 原始共享 policy 基线 |
| `stage1_to_2a_shared` | `531 / 600 = 0.885` | `43 / 600 = 0.072` | `235 / 300 = 0.783` | 第一课程 best 接回 2 车 A |

纵向结论：

- 第一课程 warm-start 后的 2 车 A 不只是“能接回主线”，而是普通 2 车测试明显好于旧 2 车 A。
- 提升主要体现在 full success，从 `0.603` 提到 `0.783`，说明两车同时完成任务的比例提高。
- collision 从 `0.117` 降到 `0.072`，说明第一课程补到的局部导航能力对普通 2 车也有正向迁移。
- 这支持下一步进入 2 车 D 主线机制，而不是继续在 2 车 A 上加练。

测试日志：

- `logs/test/test_multi_stage1_to_2a_shared_TD3_velodyne_multi_v4_curriculum_stage2_2a_shared_from_stage1g_best_detached_20260606_091850.log`

checkpoint:

- `TD3/checkpoints/TD3_velodyne_multi_v4_curriculum_stage2_2a_shared_from_stage1g_best.pt`

运行命令：

```bash
scripts/start_training_detached_multi_stage1_to_2a_shared.sh
```

停止命令：

```bash
scripts/stop_training_detached_multi_stage1_to_2a_shared.sh
```

## 主线推进：2车D

目标：从第一课程增强后的 2车A，继续接回主线 D 设置：

- 共享 policy
- 动态 reward
- 距离加权 reward
- 局部邻域 critic

### 2D 直接接入：失败

`stage2_2d_local_critic_from_2a` 的做法：

- actor 从 `stage2_2a_shared_from_stage1g_best` warm-start
- local critic 因输入维度改变，重新初始化
- actor lr: `0.00006`
- critic lr: `0.00008`
- exploration noise: `0.08`
- actor 立刻开始更新

结果不好：

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.025 | 0.825 | 0.150 | 0.000 | 0.300 |
| 2 | 0.412 | 0.575 | 0.013 | 0.150 | 0.025 |
| 3 | 0.350 | 0.487 | 0.163 | 0.100 | 0.300 |
| 4 | 0.512 | 0.400 | 0.100 | 0.275 | 0.175 |
| 5 | 0.475 | 0.500 | 0.025 | 0.200 | 0.050 |
| 6 | 0.637 | 0.325 | 0.037 | 0.375 | 0.075 |
| 7 | 0.637 | 0.312 | 0.062 | 0.350 | 0.125 |

直观看到的问题：

- 朝目标直冲，容易撞。
- 掠过目标或绕目标转。
- 局部摆动。

判断：这不是 2车A 不好，而是 A 到 D 的阶段切换太急。D 的 critic 是新初始化的，如果马上用它更新 actor，容易把已经学好的 actor 带偏。

失败日志：

- `logs/failed/train_multi_stage2_2d_local_critic_from_2a_detached_20260606_101512.log`

### 2D 保守接入：当前正在跑

`stage2_2d_local_critic_from_2a_guarded` 的核心是：**保留 actor，重置 critic，重新调学习率和探索噪声，并先冻结 actor。**

- actor warm-start: `stage2_2a_shared_from_stage1g_best`
- critic: 重新初始化
- actor update delay: `15000` agent samples
- actor lr: `0.00002`
- critic lr: `0.00008`
- exploration noise: `0.12`
- exploration min: `0.03`
- best metric: `full_success`

这一步对应阶段切换时需要处理的变量：

| 变量 | 处理 |
| --- | --- |
| actor 权重 | 保留，从 2车A best 接上 |
| critic 权重 | 重置，因为 D 的 critic 输入维度变了 |
| actor 学习率 | 降低，避免破坏已有 actor |
| critic 学习率 | 保持可学习，让新 critic 尽快适应 |
| 探索噪声 | 重新设为中等，不完全重头探索，也不太保守 |
| actor 更新 | 前 15000 samples 冻结，只训练 critic |

判断标准：

- 前 2 个 eval 不应再出现 `collision_rate > 0.5`。
- 6 个 epoch 左右希望达到 `success_rate >= 0.80` 或 `full_success_rate >= 0.60`。
- 如果仍然直冲、绕圈、摆动，就不继续硬训，改做 dynamic reward / local critic 消融。

运行命令：

```bash
scripts/start_training_detached_multi_stage2_2d_local_critic_from_2a_guarded.sh
```

停止命令：

```bash
scripts/stop_training_detached_multi_stage2_2d_local_critic_from_2a_guarded.sh
```

## 直接三车密集尝试

`stage2a_manual_dense_crossing` 从 `stage1g best` warm-start 后，前 4 个 eval 没有形成上升趋势：

| epoch | success_rate | collision_rate | full_success_rate | timeout_episode_rate |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.521 | 0.389 | 0.208 | 0.125 |
| 2 | 0.465 | 0.521 | 0.125 | 0.083 |
| 3 | 0.403 | 0.590 | 0.125 | 0.062 |
| 4 | 0.507 | 0.486 | 0.083 | 0.083 |

结论：直接进入三车密集交互跨度太大，当前结果作为“过难尝试”保留，不作为主线继续训练。

日志：

- `logs/too_hard/train_multi_curriculum_stage2a_manual_dense_crossing_detached_20260605_152613.log`

## 预热训练口径

- agents: 2
- case file: `../cases/stage2_pre_pairwise_warmup_cases.json`
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best`
- actor lr: `0.00004`
- critic lr: `0.00004`
- exploration noise: `0.045`
- exploration min: `0.015`
- max epochs: 6
- eval episodes: 48
- local-navigation reward: on
- dynamic interaction reward: light `interaction_only`

这里的交互 reward 只作为轻量防撞压力，不改变 actor 输入维度；目标是先让模型在简单双车交互中学会减速、绕开、错峰接近目标，再回到三车人工密集。

## 双车预热结果

`stage2_pre_pairwise_warmup` 从 `stage1g best` warm-start，跑满 6 个 epoch。best checkpoint 在 epoch 1，后续没有继续变好：

| epoch | success_rate | collision_rate | full_success_rate | timeout_episode_rate |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.719 | 0.292 | 0.583 | 0.021 |
| 2 | 0.583 | 0.427 | 0.396 | 0.042 |
| 3 | 0.510 | 0.531 | 0.354 | 0.000 |
| 4 | 0.604 | 0.427 | 0.500 | 0.021 |
| 5 | 0.635 | 0.396 | 0.500 | 0.000 |
| 6 | 0.604 | 0.396 | 0.458 | 0.042 |

判断：双车预热比直接三车密集容易，但仍没有学成稳定交互策略，collision 仍然偏高。继续用当前 reward 和 case 续训的收益不明确，下一步应先复盘失败 case 或降低交互 reward 干扰，再决定是否重新跑预热。

日志：

- valid: `logs/train/train_multi_curriculum_stage2_pre_pairwise_warmup_detached_20260605_170738.log`
- failed startup: `logs/failed/train_multi_curriculum_stage2_pre_pairwise_warmup_detached_20260605_170534.log`

## 双车诊断

双车预热里 collision 仍偏高，因此先测、不训练。诊断集把双车交互拆成同向、轻交叉、正面对穿和目标区合流，分别测试 `stage1g best` 与双车预热 best。

case file: `../cases/stage2_pairwise_diagnostic_cases.json`

### `stage1g best` 结果

测试 160 个 episode，每个 case 10 次，模型为 `TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best`。

整体结果：

| 指标 | 数值 |
| --- | ---: |
| agent success | 222 / 320 = 0.694 |
| agent collision | 70 / 320 = 0.219 |
| agent unresolved | 28 / 320 = 0.088 |
| full success | 88 / 160 = 0.550 |
| timeout episode | 21 / 160 = 0.131 |

case 结果：

| case | success | collision | full success | timeout | 判断 |
| --- | ---: | ---: | ---: | ---: | --- |
| `goal_merge_close_center` | 1.000 | 0.000 | 1.000 | 0.000 | 稳定 |
| `goal_merge_easy_a` | 0.950 | 0.000 | 0.900 | 0.100 | 基本可用 |
| `goal_merge_easy_b` | 1.000 | 0.000 | 1.000 | 0.000 | 稳定 |
| `goal_merge_wall_a` | 0.150 | 0.000 | 0.000 | 1.000 | 贴墙目标汇合失败 |
| `head_on_offset_lane` | 0.650 | 0.300 | 0.600 | 0.100 | 不稳定 |
| `head_on_symmetric_center` | 0.650 | 0.250 | 0.500 | 0.200 | 不稳定 |
| `head_on_wall_offset` | 0.800 | 0.200 | 0.700 | 0.000 | 可用但需防撞 |
| `head_on_wall_side` | 0.900 | 0.100 | 0.800 | 0.000 | 基本可用 |
| `offset_cross_easy_a` | 0.700 | 0.100 | 0.500 | 0.400 | 交叉等待失败 |
| `offset_cross_easy_b` | 0.600 | 0.400 | 0.400 | 0.000 | 交叉碰撞偏高 |
| `perpendicular_cross_center` | 0.650 | 0.350 | 0.500 | 0.000 | 交叉碰撞偏高 |
| `perpendicular_cross_staggered` | 0.500 | 0.350 | 0.300 | 0.300 | 交叉不稳定 |
| `same_direction_far_lane_a` | 0.700 | 0.300 | 0.600 | 0.000 | 简单双车也有碰撞 |
| `same_direction_far_lane_b` | 1.000 | 0.000 | 1.000 | 0.000 | 稳定 |
| `same_direction_overtake_light` | 0.400 | 0.600 | 0.000 | 0.000 | 同向追越失败 |
| `same_direction_wall_parallel` | 0.450 | 0.550 | 0.000 | 0.000 | 靠墙并行失败 |

结论：

- `stage1g best` 不是不能迁移到双车，普通目标汇合、部分会车可以完成。
- 失败集中在“同向接近时的速度协调”、“交叉路口的先后顺序”、“贴墙目标附近的等待/绕行”。
- 第二课程不应直接推进三车密集，也不应继续泛泛训练双车随机；应该把上述三类失败作为核心样本。
- 下一步用同一诊断集测试双车预热 best。如果双车预热 best 没有明显改善，说明当前预热设置没有学到有效交互语义，需要重做预热设置。

日志：

- `logs/test/test_multi_curriculum_stage2_pairwise_diagnostic_TD3_velodyne_multi_v4_curriculum_stage1g_collision_guard_from_stage1f_best_detached_20260605_200327.log`

### 双车预热 best 结果

测试 160 个 episode，每个 case 10 次，模型为 `TD3_velodyne_multi_v4_curriculum_stage2_pre_pairwise_warmup_from_stage1g_best`。

整体结果：

| 指标 | 数值 | 相对 `stage1g best` |
| --- | ---: | ---: |
| agent success | 235 / 320 = 0.734 | +0.041 |
| agent collision | 79 / 320 = 0.247 | +0.028 |
| agent unresolved | 9 / 320 = 0.028 | -0.059 |
| full success | 101 / 160 = 0.631 | +0.081 |
| timeout episode | 8 / 160 = 0.050 | -0.081 |

case 结果：

| case | success | collision | full success | timeout | 判断 |
| --- | ---: | ---: | ---: | ---: | --- |
| `goal_merge_close_center` | 1.000 | 0.050 | 1.000 | 0.000 | 稳定，略有碰撞噪声 |
| `goal_merge_easy_a` | 0.900 | 0.200 | 0.800 | 0.000 | 可用但碰撞升高 |
| `goal_merge_easy_b` | 1.000 | 0.000 | 1.000 | 0.000 | 稳定 |
| `goal_merge_wall_a` | 0.650 | 0.050 | 0.400 | 0.500 | 明显改善但仍不稳 |
| `head_on_offset_lane` | 0.800 | 0.200 | 0.800 | 0.000 | 改善 |
| `head_on_symmetric_center` | 0.350 | 0.600 | 0.300 | 0.100 | 退化，硬伤 |
| `head_on_wall_offset` | 0.800 | 0.200 | 0.700 | 0.000 | 基本持平 |
| `head_on_wall_side` | 0.950 | 0.050 | 0.900 | 0.000 | 改善 |
| `offset_cross_easy_a` | 0.800 | 0.100 | 0.600 | 0.200 | 改善但仍会等待失败 |
| `offset_cross_easy_b` | 0.750 | 0.250 | 0.600 | 0.000 | 改善 |
| `perpendicular_cross_center` | 0.300 | 0.700 | 0.300 | 0.000 | 明显退化，硬伤 |
| `perpendicular_cross_staggered` | 0.650 | 0.350 | 0.600 | 0.000 | full success 改善但碰撞仍高 |
| `same_direction_far_lane_a` | 0.950 | 0.050 | 0.900 | 0.000 | 明显改善 |
| `same_direction_far_lane_b` | 0.950 | 0.050 | 0.900 | 0.000 | 略低于 `stage1g best`，仍可用 |
| `same_direction_overtake_light` | 0.600 | 0.400 | 0.300 | 0.000 | 从 0 提升，但仍不稳 |
| `same_direction_wall_parallel` | 0.300 | 0.700 | 0.000 | 0.000 | 仍失败，且碰撞更高 |

对照结论：

- 双车预热 best 有学习效果，full success 从 0.550 提到 0.631，timeout 明显下降。
- 改善主要来自贴墙目标汇合、错位交叉、同向远距离和同向追越；说明双车预热不是完全无效。
- 碰撞率从 0.219 升到 0.247，说明当前预热更偏向“抢过”，没有形成稳定让行。
- 剩余硬伤非常集中：靠墙并行、垂直中心交叉、对称迎面。这三类应组成下一轮训练核心，而不是继续扩大到三车。

日志：

- `logs/test/test_multi_curriculum_stage2_pairwise_diagnostic_TD3_velodyne_multi_v4_curriculum_stage2_pre_pairwise_warmup_from_stage1g_best_detached_20260605_204725.log`

## 下一步判断

第二课程下一步不直接回到三车密集。新开“主线：双车让行修复”阶段，从双车预热 best warm-start，训练样本围绕三类硬伤，并保留少量已会 case 防止退化：

- 靠墙并行：修复 `same_direction_wall_parallel` 的稳定碰撞。
- 垂直中心交叉：修复 `perpendicular_cross_center` 的高碰撞。
- 对称迎面：修复 `head_on_symmetric_center` 的抢行。

训练设置：

- case file: `../cases/stage2_main_pairwise_repair_cases.json`
- warm-start: `TD3_velodyne_multi_v4_curriculum_stage2_pre_pairwise_warmup_from_stage1g_best`
- actor lr: `0.00002`
- critic lr: `0.00003`
- exploration noise: `0.025`
- exploration min: `0.008`
- dynamic reward: on
- reward mode: `average`
- distance-weighted reward: on
- reward self weight: `0.8`
- local critic: on
- active-neighbor filtering: on
- replay buffer: 重置，让新样本占主导
- eval: 训练内看当前修复集；训练后固定用 `stage2_pairwise_diagnostic` 做完整对照

注意：`stage2_pre_pairwise_warmup` 是旁路预热，未启用局部邻域 critic。`stage2_main_pairwise_repair` 才回到当前主线机制。

## 运行命令

```bash
scripts/start_training_detached_multi_curriculum.sh stage2_pre_pairwise_warmup
```

主线双车修复：

```bash
scripts/start_training_detached_multi_curriculum.sh stage2_main_pairwise_repair
```

修复稳定后再回到三车密集：

```bash
DRL_MULTI_LOAD_MODEL_NAME=TD3_velodyne_multi_v4_curriculum_stage2_main_pairwise_repair_from_stage2_pre_best \
scripts/start_training_detached_multi_curriculum.sh stage2a_manual_dense_crossing
```
