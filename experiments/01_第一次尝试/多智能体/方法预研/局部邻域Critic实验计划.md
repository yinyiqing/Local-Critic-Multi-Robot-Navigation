# 局部邻域 Critic 实验计划

> 历史记录：本文档记录局部邻域 Critic 从两车机制验证到三车局部邻域 Critic 验证的设计过程。D/D2 区分和三车历史结果请以 `experiments/01_第一次尝试/多智能体/README.md` 与 `experiments/01_第一次尝试/多智能体/3智能体/三车主线对照总表.md` 为准。

## 研究问题

现有多智能体实验已经验证共享 policy 可以跑通，也验证了邻域 reward 融合具有一定效果。但这些实验仍然把每个机器人基本当作独立样本处理：actor 和 critic 主要基于单个机器人的观测与动作工作，邻居信息没有进入价值评估模型。

本实验要验证：

> 在共享 policy 框架下，参考 MADDPG/CTDE 思想，让 critic 在训练阶段看到本机器人雷达范围内的邻居信息，是否能比仅做 reward 融合更稳定地提升多机器人协同表现？

## 实验假设

1. 相比只融合 reward，让 critic 显式观察邻居信息能更准确估计多机器人交互下的动作价值。
2. 只开放雷达范围内的邻居信息，比直接输入全局所有机器人信息更符合局部导航任务，也能减少远处无关机器人带来的噪声。
3. 固定最大邻居槽位、按距离排序、超出范围补零，可以兼容 2 车到 10 车实验，避免后期因机器人数量变化频繁改网络结构。

## 方法设计

### Actor

根据阶段反馈，actor 输入维度保持不变。执行阶段最终只部署 actor，且假设机器人之间没有通信，因此每个机器人只能使用自身 observation：

```text
actor_input_i = obs_i
```

也就是说，actor 仍为 24 维输入，不接收邻居 observation、邻居相对位置或邻居动作。邻居信息只在训练阶段开放给 critic，保持 centralized training, decentralized execution。

### Critic

将 critic 输入从：

```text
critic_input_i = [obs_i, action_i]
```

扩展为：

```text
critic_input_i = [obs_i, action_i, neighbor_context_i]
```

`neighbor_context_i` 由当前机器人雷达范围内的其他机器人构成，按距离从近到远排序。超出雷达范围或不存在的邻居槽位用 0 补齐，并用 `visible_mask` 标记。

初版邻居特征：

```text
relative_x
relative_y
distance
bearing
neighbor_linear_action
neighbor_angular_action
visible_mask
```

初版按 10 车目标预留输入结构：

```text
MAX_AGENTS = 10
K = MAX_AGENTS - 1 = 9
critic_state_dim = 24 + 9 * 7 = 87
critic_action_dim = 2
```

代码实现中，critic 的 state/context 分支为 87 维，动作 `action_i` 通过 action 分支进入 critic；从概念上看，critic 评价的是 `[obs_i, neighbor_context_i, action_i]`。即使先做 2 车或 3 车验证，critic 的 state/context 维度也保持不变。实际不存在或不可见的邻居全部填 0，这样后续扩展到 5 车、10 车时不需要更换网络输入结构。

### Reward

初版保留距离加权 reward 作为辅助训练信号：

```text
w_j = exp(-distance_j / sigma)
neighbor_reward_i = sum(w_j * reward_j) / sum(w_j)
reward_i = alpha * own_reward_i + (1 - alpha) * neighbor_reward_i
```

初始参数：

```text
alpha = 0.8
sigma = 2.0
```

无可见邻居时使用自身 reward。为了分清 critic 改动和 reward 改动的贡献，后续需要保留 reward-only 对照。

## 实验阶段

### 阶段零：环境容量验证

目的：在正式训练前确认当前 Gazebo 环境是否能支持更多机器人，避免后期因为地图太小、机器人太密或仿真性能不足导致实验结论失真。

检查配置：

```text
N = 2, 3, 5, 10
```

重点检查：

- 机器人能否稳定 spawn 和 reset
- goal 采样是否过近、过密或经常落在障碍物附近
- 初始位置是否容易互相阻塞
- `/velodyne_points`、odom、cmd_vel 等 topic 是否稳定
- Gazebo 实时率和训练步频是否可接受
- 不训练随机运行时，碰撞和卡死是否明显随 N 增大失控

执行文档见：`环境容量验证.md`。

### 阶段一：两车机制验证

目的：验证局部邻域 critic 的代码路径和训练流程是否正确。

配置：

```text
N = 2
K = 9
```

重点检查：

- 邻居相对位置、距离、方位计算是否正确
- mask 和补零是否正确
- replay buffer 是否正确保存当前和下一步 neighbor context
- critic 输入维度变化后训练是否稳定
- 距离加权 reward 是否能正常产生有效训练信号

阶段一不作为最终结论，只用于机制验证和初步对比。

### 阶段二：三车局部邻域 Critic 验证

目的：验证按距离排序的多邻居输入是否有效。

配置：

```text
N = 3
K = 9
```

重点观察：

- 多邻居排序是否稳定
- full success rate 是否优于 weighted08
- timeout rate 是否下降
- critic 是否比 reward-only 方法更稳定

### 阶段三：五车和十车扩展性验证

目的：验证局部邻域 critic 在更高机器人密度下是否仍有效。

建议配置：

```text
N = 5, K = 9
N = 10, K = 9
```

核心要求：

- critic 输入结构固定，实际可见邻居由雷达范围和 mask 决定
- 测试局部邻域方法在多车场景下是否比 reward-only 方法更稳
- 若 10 车明显受限于地图容量或仿真性能，保留 5 车作为主要扩展结果，并记录 10 车失败原因

## 对照设置

为避免 warm-start 带来的公平性问题，所有对照实验应使用相同初始模型、训练预算、评估频率和测试规模。

建议至少包含四组：

| 组别 | 初始化 | Reward | Critic 输入 |
| --- | --- | --- | --- |
| A | `TD3_velodyne_multi_v4` | individual reward | `[obs_i, action_i]` |
| B | `TD3_velodyne_multi_v4` | weighted08 reward | `[obs_i, action_i]` |
| C | `TD3_velodyne_multi_v4` | 距离加权 reward | `[obs_i, action_i]` |
| D | `TD3_velodyne_multi_v4` | 距离加权 reward | `[obs_i, action_i, neighbor_context_i]` |

测试阶段统一关闭训练 reward shaping，使用 individual reward 统计结果。

## 评价指标

主要指标：

- `success_rate`
- `full_success_rate`
- `collision_rate`
- `timeout_rate`
- `avg_final_distance`
- `completion_ratio`
- `success_80_rate`

优先判断顺序：

1. `full_success_rate` 是否提升
2. `timeout_rate` 是否下降
3. `collision_rate` 是否保持可控
4. `avg_final_distance` 是否下降

只降低碰撞但显著增加 timeout，不视为有效改进。

## 主要风险

1. critic 输入维度变化后，旧 critic 权重不能直接完整复用。
2. replay buffer 需要扩展，否则 critic 无法训练邻居 context。
3. 两车结果可能不足以证明方法优势，必须继续做三车以上实验。
4. 多车 Gazebo 仿真开销较大，需要先做环境容量验证。
5. 如果地图对 10 车过于拥挤，结果可能主要反映环境容量限制，而不是算法能力。

## 阶段结论标准

阶段一成功标准：

- 训练和测试流程稳定运行
- local critic 指标不明显劣于 weighted08
- 日志能正确记录 neighbor context、mask 和距离加权 reward

阶段二成功标准：

- 三车场景下 `full_success_rate` 或 `timeout_rate` 优于 weighted08
- 多邻居排序和 mask 机制稳定

阶段三成功标准：

- 五车或十车场景下仍能保持可训练性
- 局部邻域 critic 相比 reward-only 有更好的稳定性或效率

## 当前执行建议

2026-05-19 的环境容量验证显示，2 车和 3 车可以稳定 reset 与运行；5 车开始出现 goal 采样失败和 odom 超时；10 车当前无法完成有效 reset。

因此下一步仍按两级推进：

1. 先用 2 车完成局部邻域 critic 的机制验证，确认 critic context、mask、replay buffer、checkpoint 和测试流程全部正确。
2. 再用 3 车作为第一组正式小规模多邻居实验，验证排序和多邻居输入是否带来稳定收益。

5 车和 10 车暂不直接进入训练，等 2 车机制验证和 3 车小规模实验通过后，再单独处理地图容量、目标采样和仿真性能问题。

## 主线可行性判断

该方向具备继续推进潜力，但需要从工程验证推进到系统实验。仅有两车结果不足以支撑完整结论；至少需要完成公平消融、多车扩展、对比方法和多场景验证。

如果实验结果支持假设，核心贡献可以表述为：

> 一种面向多机器人局部交互的 centralized critic，只在训练阶段引入感知范围内的邻居信息，并结合距离加权 reward，提高共享 policy 多机器人导航的协同稳定性。
