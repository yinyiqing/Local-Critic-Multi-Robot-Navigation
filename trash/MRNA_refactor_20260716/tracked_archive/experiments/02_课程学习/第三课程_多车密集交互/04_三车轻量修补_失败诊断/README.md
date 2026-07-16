# 04 三车轻量修补：失败诊断

作用：从课程 3D2 best 出发，只训练 3 个较轻的手工三车交互 case，试探是否能小幅修补密集交互碰撞问题。

结论：暂停，不继续训练。

## 为什么停

- RViz 观察到绕目标、掠过目标、远离目标的现象重新出现。
- eval 从 epoch 1 到 epoch 4 持续走低：

| epoch | success | collision | full success | timeout |
| --- | ---: | ---: | ---: | ---: |
| 1 | `0.676` | `0.324` | `0.389` | `0.056` |
| 2 | `0.639` | `0.361` | `0.306` | `0.028` |
| 3 | `0.556` | `0.463` | `0.139` | `0.000` |
| 4 | `0.500` | `0.426` | `0.111` | `0.278` |

## 关键判断

- 这不是这次轻量修补才突然坏。
- 课程 3D2 训练前期很好，best 在 epoch 3：
  - success `0.975`
  - collision `0.033`
  - full success `0.925`
- 课程 3D2 后段已经开始退化：
  - epoch 10 full success 掉到 `0.300`
  - epoch 13 掉到 `0.025`
  - epoch 16 掉到 `0.000`
- 说明主线当前可用的是 early best，不是 latest。

## 暂定解释

当前现象更像是策略在“朝目标走”和“避障/转向”之间形成坏循环，而不是单纯相互躲避。

另外，`context_neighbors_mean=0` 目前不能直接当成 local critic 没看到邻居的证据，因为日志里记录的是 episode 末尾的 context，不是整段 episode 的平均 context。后续如果要查 local critic，需要重新加更可靠的诊断统计。

## 下一步

先不继续第三课程训练。

优先查：

1. 为什么课程 3D2 从 epoch 10 后明显退化。
2. local critic 的邻居 context 在训练过程中到底是否有效。
3. actor 更新后是否把 early best 的稳定导航能力破坏了。

当前主线仍保留课程 3D2 best。

## 已加诊断字段

为了避免继续误判，训练日志已补充：

- `context_step_mean`：整段 episode 中 local critic 平均看到几个邻居。
- `context_step_max`：整段 episode 中 local critic 最多看到几个邻居。
- `actor_unlocked`：actor 是否已经开始跟随 critic 梯度更新。

下一次只需要短跑诊断，不需要长训练。重点看退化是否发生在 `actor_unlocked=1` 之后。

## 追加诊断：actor 解锁对照

后来补了两次短诊断，专门验证“是不是 actor 一更新就把策略带坏”。

### 1. actor 解锁版：`20260608_124049`

设置：

- warm start：课程 3D2 best
- 模型：`TD3_velodyne_multi_v4_diag_stage3_light_patch_actor_unlock`
- actor update delay：`7000` agent samples
- max epochs：`4`
- eval episodes：`24`

结果：

| epoch | success | collision | full success | timeout |
| --- | ---: | ---: | ---: | ---: |
| 1 | `0.625` | `0.361` | `0.333` | `0.042` |
| 2 | `0.458` | `0.556` | `0.125` | `0.083` |
| 3 | `0.444` | `0.486` | `0.125` | `0.250` |
| 4 | `0.250` | `0.667` | `0.000` | `0.250` |

actor 在 `agent_samples=7004` 左右开始解锁：`actor_unlocked=1`。

### 2. actor 冻结版：`20260608_152330`

设置：

- warm start：课程 3D2 best
- 模型：`TD3_velodyne_multi_v4_diag_stage3_light_patch_actor_frozen`
- actor update delay：`999999999`，本次基本不解锁
- max epochs：`3`
- eval episodes：`24`

结果：

| epoch | success | collision | full success | timeout |
| --- | ---: | ---: | ---: | ---: |
| 1 | `0.639` | `0.403` | `0.333` | `0.000` |
| 2 | `0.597` | `0.403` | `0.375` | `0.000` |
| 3 | `0.611` | `0.417` | `0.375` | `0.000` |

全程没有出现 `actor_unlocked=1`。

### 对照结论

- local critic 在 episode 过程中能看到邻居：`context_step_mean` 非零，`context_step_max=2`。
- actor 解锁版从 `full_success=0.333` 掉到 `0.000`。
- actor 冻结版没有继续塌到 `0.000`，并在 epoch 2/3 保持 `0.375`。
- 因此这轮轻量修补的主要问题不是“critic 完全看不到邻居”，而是 actor 更新后容易被不稳定梯度带坏。

后续如果还要修第三课程，应优先做保守 actor 更新，例如更低 actor LR、更少 actor update、只更新 actor 后层，或者加 old-actor action distillation；不要直接全量解冻 actor 长训。
