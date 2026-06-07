# 第二课程：多车人工密集交互

## 目的

第二课程从第一课程的单车 best warm-start，不再继续单独补墙边 case，而是让同一个 policy 开始处理多车交错、靠近、会车、目标区域聚集等交互压力。

这一步要回答两个问题：

- 第一课程学到的单车局部能力迁移到多车后会不会重新出现左右摇摆、局部停滞或撞墙。
- 多车失败主要来自交互压力，还是仍然来自单车墙边局部导航缺陷。

## 当前阶段

第二课程分成两段。A 段是“主线接回”，确认第一课程能接回 2车A 和 2车D；B 段才是“多车手工密集交互”，用手工起点和目标点制造交叉、靠近、汇合、会车。

| 主线步骤 | 状态 | 作用 |
| --- | --- | --- |
| 1. `stage1_to_2a_shared` | completed | 第一课程 best 接回 2车A，共享 policy 普通测试优于旧 2车A。 |
| 2. `stage2_2d_local_critic_from_2a_gentle` | completed | 从 2车A best 接 2车D；best 在 epoch 5，后续 actor 更新让性能下降。 |
| 3. `stage2_2d_local_critic_from_2a_gentle_best` 固定测试 | completed | 300 集普通测试略好于 2车A best，可以作为当前 2D 主线节点。 |
| 4. `stage2b_three_light_dense` 诊断 | completed | 三车轻密集整体碰撞很高，不能直接训练。 |
| 5. `stage2_to_3a_shared_from_2d_gentle` | active | 先回普通 3车A，确认三车共享 policy 主线能否接上。修正后必须 actor-only warm-start。 |
| 6. 三车D或三车密集课程 | pending | 3A 成立后再决定接 3D，或进入手工密集课程。 |

旁路记录不作为当前主线继续：

| 记录 | 结论 |
| --- | --- |
| `stage2_2d_local_critic_from_2a` | 直接接 2车D 失败，原因是新 critic 还没稳定就立刻更新 actor。 |
| `stage2_2d_local_critic_from_2a_guarded` | 冻结 actor 前 3 个 epoch 很好，解冻后崩，说明 actor 更新太强。 |
| `stage2_pairwise_diagnostic` | 诊断集，只用于定位双车交互短板。 |
| `stage2_pre_pairwise_warmup` | 有一点效果但不稳定，collision 偏高，不作为主线继续。 |
| `stage2_main_pairwise_repair` | 路线复位前的过早尝试，暂停。 |
| `stage2a_manual_dense_crossing` | 直接上三车太难，暂停。 |
| `stage2_to_3a_shared_from_2d_gentle` 第一次启动 | 加载 2D gentle best 时强行加载 critic，critic 结构不兼容，导致随机初始化；这次结果不作为算法结论。 |

## 当前必须注意

从 2车D 接普通 3车A 时，只能加载 actor。

原因很简单：2车D 用了局部邻域 critic，3车A 不用局部邻域 critic，critic 输入结构不同。若按完整模型加载，会失败并随机初始化。正确做法是：

- actor 从 `TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best` 加载。
- critic 按 3车A 结构重新初始化。
- 训练日志开头必须看到 `Loaded initial actor parameters from:`。
- 如果看到 `Could not load the stored model parameters, initializing randomly`，这条训练要立刻停掉。

失败记录：

- log: `logs/failed/train_multi_stage2_to_3a_shared_detached_20260607_090302.log`
- 这次产生的 checkpoint/model 是随机初始化结果，已删除，避免后续误用。

## 第二课程B：三车轻密集

第二课程B不直接上最难三车。当前先做 `stage2b_three_light_dense`，它是三车轻密集诊断集：

- 三车轻交叉：中心交叉但错开一点。
- 三车轻对穿：对穿但横向留距。
- 目标轻汇合：目标靠近但不完全重叠。
- 起点轻聚集：起点靠近，目标分散。
- 同向轻追越：同向移动但有错峰。
- 靠墙轻会车：靠墙区域有会车压力但不贴死。

诊断结果：`stage2b_three_light_dense` 不是合适的直接训练入口。它能完成目标轻汇合，但在三车交叉、同向错峰、起点聚集上几乎都是碰撞。

120 集诊断整体：

- agent success: `163 / 360 = 0.453`
- agent collision: `198 / 360 = 0.550`
- agent unresolved: `2 / 360 = 0.006`
- full success: `24 / 120 = 0.200`
- timeout: `2 / 120 = 0.017`

分 case 结果：

| case | success | collision | full success | 判断 |
| --- | ---: | ---: | ---: | --- |
| 三车目标汇合_轻聚集 | 0.967 | 0.083 | 0.900 | 已会，可保留少量防退化 |
| 三车靠墙会车_轻错位 | 0.567 | 0.400 | 0.150 | 部分可用但不稳 |
| 三车轻对穿_横向留距 | 0.467 | 0.533 | 0.150 | 碰撞偏高 |
| 三车起点聚集_分散目标 | 0.383 | 0.617 | 0.000 | 失败 |
| 三车轻交叉_中心错位 | 0.183 | 0.817 | 0.000 | 失败 |
| 三车同向错峰_轻追越 | 0.150 | 0.850 | 0.000 | 失败 |

结论：从 2D gentle best 直接进入三车轻密集仍然太难。下一步不是硬训 `stage2b_three_light_dense`，而是先做 `stage2b_three_transition`：两车有冲突，第三车只轻参与，让模型先适应三车输入、三车邻域和轻交互压力。

诊断命令：

```bash
DRL_MULTI_TEST_TARGET_EPISODES=120 \
scripts/start_test_detached_multi_curriculum.sh stage2b_three_light_dense
```

诊断日志：

- `logs/test/test_multi_curriculum_stage2b_three_light_dense_TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best_detached_20260606_224522.log`

路线修正：

- `stage2b_three_transition` 曾短暂启动，但路线讨论后停止，归为过早尝试。
- 当前不继续三车过渡训练，先从普通 3车A 接回主线。

过早尝试日志：

- `logs/too_early/train_multi_curriculum_stage2b_three_transition_detached_20260607_085334.log`

当前训练命令：

```bash
scripts/start_training_detached_multi_stage2_to_3a_shared.sh
```

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

### 2D 保守接入 v1：失败

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

结果：

| epoch | success_rate | collision_rate | full_success_rate |
| ---: | ---: | ---: | ---: |
| 1 | 0.912 | 0.062 | 0.825 |
| 2 | 0.900 | 0.087 | 0.800 |
| 3 | 0.875 | 0.087 | 0.750 |
| 4 | 0.225 | 0.775 | 0.025 |
| 5 | 0.062 | 0.887 | 0.000 |
| 8 | 0.250 | 0.750 | 0.050 |

判断：前 3 个 epoch 好，说明 2车A actor 本身可以接到 D；第 4 个 epoch 开始崩，正好发生在 actor 解冻之后，说明 actor 更新仍然太强。

### 2D 温和接入：已完成

`stage2_2d_local_critic_from_2a_gentle` 只做轻微重置，不推倒重来：

- actor warm-start: `stage2_2a_shared_from_stage1g_best`
- critic: 重新初始化
- actor update delay: `25000` agent samples
- actor lr: `0.000002`
- critic lr: `0.00008`
- exploration noise: `0.10`
- exploration min: `0.03`
- best metric: `full_success`

相对 v1 guarded 的变化：

| 变量 | v1 guarded | v2 gentle | 意图 |
| --- | ---: | ---: | --- |
| actor lr | `0.00002` | `0.000002` | actor 更新再慢一个量级 |
| actor update delay | `15000` | `25000` | critic 预热更久 |
| exploration noise | `0.12` | `0.10` | 回到接近 2车A 的水平，不额外扰动太多 |
| max epochs | `12` | `10` | 先验证，不长时间硬训 |

结果：

| epoch | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.887 | 0.100 | 0.025 | 0.775 | 0.050 |
| 2 | 0.863 | 0.113 | 0.037 | 0.750 | 0.075 |
| 3 | 0.925 | 0.037 | 0.037 | 0.850 | 0.075 |
| 4 | 0.863 | 0.113 | 0.037 | 0.725 | 0.075 |
| 5 | 0.963 | 0.025 | 0.025 | 0.925 | 0.050 |
| 6 | 0.787 | 0.100 | 0.113 | 0.625 | 0.225 |
| 7 | 0.787 | 0.138 | 0.075 | 0.625 | 0.150 |
| 8 | 0.825 | 0.075 | 0.100 | 0.675 | 0.200 |
| 9 | 0.713 | 0.175 | 0.113 | 0.500 | 0.225 |
| 10 | 0.662 | 0.212 | 0.125 | 0.450 | 0.250 |

关键判断：

- 这次确实用到了第一课程：`stage1g best -> stage2_2a_shared_from_stage1g_best -> stage2_2d_local_critic_from_2a_gentle`。
- epoch 5 是 best，`full_success_rate=0.925`，明显强于训练末尾。
- epoch 6 以后开始下降，说明继续让新 local critic 更新 actor 会损伤原来 2车A actor。
- 这不是 2车A 负面影响，而是 D 阶段的 critic/actor 切换仍然不稳。
- 后续只用 `TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best` 做固定测试，不用 latest。

checkpoint:

- `TD3/checkpoints/TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best.pt`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best_actor.pth`

日志：

- `logs/train/train_multi_stage2_2d_local_critic_from_2a_gentle_detached_20260606_171206.log`

运行命令：

```bash
scripts/start_training_detached_multi_stage2_2d_local_critic_from_2a_gentle.sh
```

停止命令：

```bash
scripts/stop_training_detached_multi_stage2_2d_local_critic_from_2a_gentle.sh
```

固定测试命令：

```bash
scripts/start_test_detached_multi_stage2_2d_local_critic_from_2a_gentle.sh
```

停止测试命令：

```bash
scripts/stop_test_detached_multi_stage2_2d_local_critic_from_2a_gentle.sh
```

固定测试：

- model: `TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best`
- scenario: `standard`
- launchfile: `multi_robot_scenario_multi_2.launch`
- episodes: 300
- agent success: `540 / 600 = 0.900`
- agent collision: `42 / 600 = 0.070`
- agent unresolved: `20 / 600 = 0.033`
- full success: `244 / 300 = 0.813`
- timeout episode: `20 / 300 = 0.067`

与当前 2车A best 的 300 集普通测试对比：

| 模型 | agent success | agent collision | full success | 说明 |
| --- | ---: | ---: | ---: | --- |
| `stage2_2a_shared_from_stage1g_best` | `531 / 600 = 0.885` | `43 / 600 = 0.072` | `235 / 300 = 0.783` | 第一课程接回 2车A |
| `stage2_2d_local_critic_from_2a_gentle_best` | `540 / 600 = 0.900` | `42 / 600 = 0.070` | `244 / 300 = 0.813` | 2车D gentle best |

结论：

- 2D gentle best 在普通 2 车测试上没有破坏 2A，反而略好。
- 这说明“从 2A 接 D”这一步可以成立，但必须用 best checkpoint，不能用 latest。
- 训练中后段下降仍然是问题：local critic 继续更新 actor 会带来退化，所以后续推进三车前要先做复杂诊断集。

测试日志：

- `logs/test/test_multi_stage2_2d_local_critic_from_2a_gentle_TD3_velodyne_multi_v4_curriculum_stage2_2d_local_critic_from_2a_gentle_best_detached_20260606_214358.log`

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
