# 01 冲突验证

这一步先不急着做切换。

先回答一个最关键的问题：

**单一 actor 继续往密集场景训练时，会不会破坏它原来已经学好的普通导航能力。**

## 现在要验证什么

我们想验证的不是“dense actor 更强”这么简单，而是下面这件事：

1. 普通 actor 在普通五车场景里更稳
2. 往密集场景继续训练后，模型会更偏向密集交互
3. 但这种继续训练，可能会损伤它在普通场景里的原有能力

如果这三点成立，就可以把问题正式定义成：

**单一共享 actor 在普通导航能力和密集协同能力之间存在冲突。**

## 第一轮先用现成模型

先不训练新模型，先拿已经有的模型做交叉测试。

### A. 普通 actor 候选 1

- `TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best`

这是现在最自然的普通五车 actor。
优点是它和第三课程真实 warm start 的来源一致。

### B. 普通 actor 候选 2

- `TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best`

这是课程学习里带几何邻域 critic 的五车普通模型。
虽然它最终没有超过 `5A best`，但它更适合作为“带邻域 critic 的普通能力候选”。

### C. 密集 actor

- `TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5a_cleanstart_v2_best`

这是现在最自然的密集 actor 候选。

### D. 继续训练后的单一 actor

先选一版已经继续往 `stage3_asym_three_5` 训练过的模型，作为 overwrite 路线代表。

第一轮先看：

- `TD3_velodyne_multi_v4_curriculum_stage3_asym_three_5_joint_action_critic_midcheck_from_stage3_pair_cleanstart_v2_best_best`

后面如果需要，再补别的 `stage3_asym_three_5` 版本做对照。

## 第一轮测试矩阵

### 普通场景

先测标准五车普通场景：

- 普通 actor -> 普通场景
- 密集 actor -> 普通场景
- overwrite actor -> 普通场景

这里主要看：

- success_rate
- collision_rate
- full_success_rate

### 密集场景

再测 `stage3_asym_three_5`：

- 普通 actor -> 密集场景
- 密集 actor -> 密集场景
- overwrite actor -> 密集场景

这里主要看：

- success_rate
- collision_rate
- full_success_rate
- timeout_episode_rate

## 怎样算“冲突成立”

如果出现下面这种格局，就说明这个问题基本成立：

1. 普通 actor 在普通场景最好或最稳
2. 密集 actor / overwrite actor 在密集场景更强
3. 但 overwrite actor 在普通场景明显差于普通 actor

这就说明：

- 往 dense 继续训练不是“纯增益”
- 它会带来能力偏移
- 也就是我们想说的 preserve-and-specialize 动机

## 当前记录

### 当前候选收缩

普通 actor 不再从所有历史五车模型里乱选。

当前只保留 2 个最值得继续看的普通候选：

1. `5A best`
   - `TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best`
2. `5D best`
   - `TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best`

密集 actor 当前先保留：

1. `stage3_asym_pair_5 best`
   - `TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5a_cleanstart_v2_best`

补充说明：

- `2026-07-12` 起，这个 `PAIR(from_5a)` 不再默认视为最终 dense actor 候选。
- 原因很直接：`5A` 的交互底子偏弱，作为 dense 专门化 warm start 不够自然。
- 已补开一条新线：`5D -> stage3_asym_pair_5`，后面用它和旧 `PAIR(from_5a)` 再比较。

overwrite actor 当前先保留：

1. `joint_action_critic_midcheck best`
   - `TD3_velodyne_multi_v4_curriculum_stage3_asym_three_5_joint_action_critic_midcheck_from_stage3_pair_cleanstart_v2_best_best`

### 已完成

1. `5A best -> stage3_asym_three_5`
   - 120 episodes
   - `success_rate=0.885`
   - `collision_rate=0.118`
   - `full_success_rate=0.567`
2. `stage3_asym_pair_5 best -> 标准五车`
   - 120 episodes
   - `success_rate=0.885`
   - `collision_rate=0.087`
   - `full_success_rate=0.542`
   - `timeout_episode_rate=0.142`
3. `5D best -> 标准五车`
   - 120 episodes
   - `success_rate=0.882`
   - `collision_rate=0.098`
   - `full_success_rate=0.550`
   - `timeout_episode_rate=0.100`
   - 补充观察：
     - 前 100 episode 一度到过 `full_success_rate=0.600`
     - 最后 20 episode 明显变差
     - 说明 `5D` 在标准五车上没有明显优于 `5A`
4. `5D best -> stage3_asym_three_5`
   - 120 episodes
   - `success_rate=0.902`
   - `collision_rate=0.097`
   - `full_success_rate=0.650`
   - `timeout_episode_rate=0.017`
   - case 观察：
     - `three_cross_main_pair_with_late_third`
       - `success_rate=0.830`
       - `collision_rate=0.170`
       - `full_success_rate=0.475`
     - `three_goal_merge_main_pair_with_outer_third`
       - `success_rate=1.000`
       - `collision_rate=0.005`
       - `full_success_rate=1.000`
     - `three_wall_pair_with_far_third`
     - `success_rate=0.875`
     - `collision_rate=0.115`
     - `full_success_rate=0.475`
5. `THREE_MID -> 标准五车`
   - 120 episodes
   - `success_rate=0.870`
   - `collision_rate=0.115`
   - `unresolved_rate=0.018`
   - `full_success_rate=0.517`
   - `timeout_episode_rate=0.083`
   - 补充观察：
     - 前段一度表现正常
     - 后半程明显变差
     - 最后 10 个 episode 只有 `full_success_rate=0.200`
     - 说明 overwrite 后，普通场景能力确实被破坏了
6. `THREE_MID -> stage3_asym_three_5`
   - 120 episodes
   - `success_rate=0.870`
   - `collision_rate=0.130`
   - `unresolved_rate=0.005`
   - `full_success_rate=0.517`
   - `timeout_episode_rate=0.025`
   - case 观察：
     - `three_cross_main_pair_with_late_third`
       - `success_rate=0.785`
       - `collision_rate=0.210`
       - `full_success_rate=0.275`
     - `three_goal_merge_main_pair_with_outer_third`
       - `success_rate=1.000`
       - `collision_rate=0.010`
       - `full_success_rate=1.000`
     - `three_wall_pair_with_far_third`
       - `success_rate=0.825`
       - `collision_rate=0.170`
       - `full_success_rate=0.275`
   - 补充观察：
     - 不仅普通场景退化
     - dense 表现也没有超过 `5A/5D`
     - 说明 overwrite 路线整体不划算
7. `PAIR -> stage3_asym_three_5`
   - 120 episodes
   - `success_rate=0.900`
   - `collision_rate=0.102`
   - `unresolved_rate=0.000`
   - `full_success_rate=0.642`
   - `timeout_episode_rate=0.000`
   - case 观察：
     - `three_cross_main_pair_with_late_third`
       - `success_rate=0.820`
       - `collision_rate=0.180`
       - `full_success_rate=0.400`
     - `three_goal_merge_main_pair_with_outer_third`
       - `success_rate=0.995`
       - `collision_rate=0.010`
       - `full_success_rate=0.975`
     - `three_wall_pair_with_far_third`
       - `success_rate=0.885`
       - `collision_rate=0.115`
       - `full_success_rate=0.550`
   - 补充观察：
     - dense 上明显强于 `5A`
     - 和 `5D` 非常接近
     - 说明它可以作为当前“专门化 actor”候选

### 当前横向对比

| 组别 | success_rate | collision_rate | full_success_rate | timeout/unresolved |
| --- | ---: | ---: | ---: | ---: |
| `5A -> 标准五车` | 0.897 | 0.087 | 0.600 | timeout 0.087 |
| `5A -> dense` | 0.885 | 0.118 | 0.567 | timeout 0.008, unresolved 0.002 |
| `5D -> 标准五车` | 0.882 | 0.098 | 0.550 | timeout 0.100 |
| `5D -> dense` | 0.902 | 0.097 | 0.650 | timeout 0.017, unresolved 0.003 |
| `PAIR -> 标准五车` | 0.885 | 0.087 | 0.542 | timeout 0.142, unresolved 0.028 |
| `PAIR -> dense` | 0.900 | 0.102 | 0.642 | timeout 0.000, unresolved 0.000 |
| `THREE_MID -> 标准五车` | 0.870 | 0.115 | 0.517 | timeout 0.083, unresolved 0.018 |
| `THREE_MID -> dense` | 0.870 | 0.130 | 0.517 | timeout 0.025, unresolved 0.005 |

### 当前判断

- `5A` 在标准五车上仍然最稳，说明它更像“普通 actor”候选
- `5D` 在 dense 上明显好于 `5A`，但在标准五车上没有超过 `5A`
- `PAIR` 回到标准五车后，collision 还行，但 `full_success` 和 `timeout` 更差；而它在 dense 上明显更强，更像“偏向密集交互的专门 actor”
- `THREE_MID` 回到标准五车后比 `5A`、`5D`、`PAIR` 都更差，说明继续覆盖式训练会破坏普通场景能力
- `THREE_MID` 在 dense 上也没有换来更强表现，说明 overwrite 不是值得继续走的方向
- 现在已经能初步看出：
  - `5A` 更偏普通场景
  - `5D` 有一点向 dense 偏移
  - `PAIR` 的 dense 偏置更明显
- `THREE_MID` 说明 overwrite 路线会进一步放大这种偏移，而且收益不够
- 当前可先采用的候选组合：
  - 普通 actor：`5A`
  - 密集 actor：`PAIR`
- `5D` 仍然值得保留，作为“过渡 actor / 强基线”备用

### 简短记录

- `2026-07-07`：`THREE_MID -> 标准五车` 首次测试因旧 ROS/Gazebo 进程残留报错，日志作废，已清环境后从 `episode 1` 重跑。
- `2026-07-07`：`THREE_MID -> 标准五车` 重跑完成，结果差于 `5A/5D/PAIR`，支持“继续覆盖训练会伤到普通能力”这个判断。
- `2026-07-08`：`THREE_MID -> dense` 跑完，dense 上也没有更强，overwrite 路线基本可以先停。
- `2026-07-12`：`PAIR -> dense` 跑完，结果接近 `5D -> dense`，当前可以把 `5A + PAIR` 作为最自然的一组保留-专门化候选。
