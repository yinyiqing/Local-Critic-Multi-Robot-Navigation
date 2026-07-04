# 后续计划：集中式 Critic 核查

## 背景

当前课程学习主线已经确认：

- 前面较简单课程是有效的
- 更复杂的五车密集阶段里，warm-start actor 本身可用
- 但 actor 一旦继续更新，就容易退化

导师给出的新建议，不是继续盲调解冻时机，而是先确认：

- 我们当前的集中式 critic / 分布式 actor 这条线，是否已经按 MADDPG / MAPPO 一类方法的关键细节改对

## 当前目标

这一轮的目标不是继续扩新实验，而是先完成一次实现核查，回答：

1. critic 现在到底“看到了什么”
2. replay buffer 现在到底“存了什么”
3. actor 更新时，其他智能体相关动作和梯度是否处理正确
4. 当前实现和标准 CTDE 思路相比，还差哪些关键细节

## 最新进展

- 已完成一组公平短对照：
  - 同场景
  - 同 warm start actor
  - 同 `2 epoch`
  - 唯一区别是 critic 是否使用 joint action
- 当前结果：
  - joint-action critic：`success_rate=0.917`，`collision_rate=0.083`，`full_success_rate=0.625`
  - context critic control：`success_rate=0.833`，`collision_rate=0.167`，`full_success_rate=0.417`
- 这说明：
  - critic 输入改法确实会影响结果
  - 现在更值得继续查 critic 语义和 buffer，而不是回去盲调 actor 解冻时机

## 核查清单

### 1. Buffer

- 当前 replay buffer 是否保存了足够的多机信息：
  - 当前时刻多机状态
  - 当前时刻多机动作
  - 下一时刻多机状态
  - done / active mask
- 如果没有，当前 critic 实际上只能算“部分多机 context critic”，而不是更标准的 centralized critic

### 2. Critic 输入

- critic 输入到底是：
  - 本机 observation + 本机 action + 邻居几何
  - 还是 joint observation + joint action
- 当前 local / geometry critic 的信息范围，与 MADDPG 风格 centralized critic 有多大差距

### 3. Actor 更新

- 以当前智能体为中心更新 actor 时：
  - 其他智能体动作是否参与 critic 计算
  - 如果参与，是否应该 detach
- 共享 actor 条件下，这里的梯度传播是否会产生不合理串扰

### 4. Target 计算与 mask

- target critic 的 next action 是如何构造的
- done / active agent / finished agent 的 mask 是否正确进入 target 和 loss
- 是否存在“已完成或非活跃 agent 仍污染 centralized critic 训练”的问题

## 完成标准

这一轮结束时，需要产出：

1. 一份“当前实现与 MADDPG / MAPPO 常见做法对照表”
2. 一份“可能影响 critic 是否真正管用的问题清单”
3. 明确下一步到底是：
   - 先修集中式 critic 实现细节
   - 还是可以转去 BC / 保守 critic / 更强 ensemble

## 暂定顺序

1. 先读我们当前训练代码和 replay buffer
2. 再对照 MADDPG / MAPPO 论文和常见实现
3. 最后整理成问题清单和修改建议

## 第一轮核查结果

### 一、和 MADDPG / MAPPO 的共同点

- 都属于训练时给 critic 更多信息、执行时 actor 只看本机观测的 CTDE 思路
- 当前实现里，actor 仍然只吃本机 state，执行阶段没有直接依赖其他车信息
- critic 端已经开始引入邻居上下文，这个方向本身没有错

### 二、当前实现和标准 CTDE 的关键差别

#### 1. buffer 里没有保存标准 joint transition

当前 `ReplayBuffer` 在 local critic 模式下只存：

- 本机 state
- 拼接后的 critic_state
- 本机 action
- reward
- done
- 本机 next_state
- next_critic_state

对应代码：

- [TD3/replay_buffer.py](/home/jiutian/Local-Critic-Multi-Robot-Navigation/TD3/replay_buffer.py:30)
- [TD3/train_velodyne_td3_multi.py](/home/jiutian/Local-Critic-Multi-Robot-Navigation/TD3/train_velodyne_td3_multi.py:1398)

这意味着当前 buffer 没有显式保存：

- 全体智能体 observation
- 全体智能体 action
- 全体智能体 next observation
- 更细的 active mask / agent mask

所以这版实现更像“本机样本 + 邻居上下文特征”，还不是更标准的 MADDPG 式 joint transition replay。

#### 2. critic 输入不是 joint obs + joint action

当前 `train_local_critic()` 中：

- critic 输入是 `critic_state`
- action 输入仍然只是当前 agent 的 action

对应代码：

- [TD3/train_velodyne_td3_multi.py](/home/jiutian/Local-Critic-Multi-Robot-Navigation/TD3/train_velodyne_td3_multi.py:323)

而 `critic_state` 的来源只是：

- 本机 state
- 邻居相对位置 / 距离 / 朝向
- 可选的邻居动作

对应代码：

- [TD3/multi_agent_velodyne_env.py](/home/jiutian/Local-Critic-Multi-Robot-Navigation/TD3/multi_agent_velodyne_env.py:641)

所以当前 critic 不是标准意义上的“联合状态-联合动作 critic”，而是“本机状态 + 局部邻居特征”的 context critic。

#### 3. actor 更新时没有显式处理其他 agent 的可学习动作

老师提到的一个关键点是：

- 以当前 agent 为中心更新 actor 时，其他 agent 的 actor 输出是否应该 detach

这在标准 MADDPG 里之所以重要，是因为 critic 会看 joint action，actor 更新时会把“其他 agent 的动作”当成固定背景，只让当前 agent 那一支保留梯度。

但我们当前实现里，actor loss 是：

- 当前 actor 生成 `actor_action`
- critic 用 `critic_state + actor_action` 算 Q

对应代码：

- [TD3/train_velodyne_td3_multi.py](/home/jiutian/Local-Critic-Multi-Robot-Navigation/TD3/train_velodyne_td3_multi.py:375)

也就是说，当前代码里压根没有“其他 agent 可学习 action 分支”进入 actor update 图里，detach 问题还没真正出现。反过来说，也说明我们这版实现和老师提到的 MADDPG 那种 centralized critic 还没完全对齐。

#### 4. next action 也不是 joint next action

当前 target 计算时：

- `next_action = self.actor_target(next_state)`
- 再喂给 `critic_target(next_critic_state, next_action)`

对应代码：

- [TD3/train_velodyne_td3_multi.py](/home/jiutian/Local-Critic-Multi-Robot-Navigation/TD3/train_velodyne_td3_multi.py:357)

这仍然只是“当前 agent 的 next action”，不是“所有 agent 的 target next actions 一起进 critic”。

### 三、目前最可疑的实现问题

按老师提醒和 MADDPG / MAPPO 常见做法对照，当前最值得优先核查的是：

1. 我们现在这版 critic 到底算不算真正的 centralized critic  
   目前看，更像局部上下文 critic，不是标准 joint critic

2. replay buffer 信息可能不够  
   如果要做更标准的 centralized critic，buffer 很可能需要显式存多机状态和多机动作

3. active / finished agent 的 mask 处理还需要再细查  
   当前只看到了 `done_bool` 和 `active_mask` 参与部分上下文构造，还没形成标准的多机训练 mask 体系

4. 即使“邻居动作”被拼进 critic_state，它们现在也只是静态特征，不是 joint action 分支  
   这和 MADDPG 里“critic 对其他 agent 动作敏感，并在 actor 更新时固定其他 agent 动作”的机制并不等价

## 对照表：MADDPG / MAPPO vs 当前实现

| 核查点 | MADDPG / MAPPO 常见做法 | 当前实现 | 判断 |
| --- | --- | --- | --- |
| actor 执行输入 | actor 只看本机局部观测 | actor 只吃本机 `state` | 一致 |
| critic 训练输入 | critic 在训练时看额外多机信息；MADDPG 常见为 joint obs + joint action，MAPPO 常见为 centralized/global/shared obs | critic 看 `critic_state + 当前 agent action`，`critic_state` 由本机 state 和邻居上下文拼接而成 | 部分一致，但不算标准 joint critic |
| replay buffer | 为 critic 提供足够的多机 transition；至少要支持 centralized input，对 MADDPG 往往还要支持 joint action | 只存本机 state、本机 action、拼接后的 critic_state、next 对应项、reward、done | 可疑，信息可能不够 |
| 其他 agent 动作的作用 | 在 MADDPG 中，其他 agent 动作直接参与 critic；更新当前 agent actor 时，其他 agent 动作通常作为固定背景 | 邻居动作只是被编码进 context 特征；不是独立 joint action 分支 | 不一致 |
| actor 更新时的梯度路径 | 当前 agent 的动作应保留梯度；其他 agent 分支通常不应一起被错误更新 | 当前实现里只有本机 actor_action 进梯度图，其他 agent 没有可学习 action 分支 | 不是“detach 写错了”，而是结构上还没到那一步 |
| target 计算 | MADDPG 常见做法是 next joint obs + next joint actions 一起进 target critic；MAPPO 也要求 centralized value 的 next 输入一致 | 当前只算 `next_state -> next_action`，再和 `next_critic_state` 配对 | 不属于标准 joint target |
| active / done mask | 多 agent 训练通常需要更细的 mask，避免已结束 agent 污染 value / critic 更新 | 当前只看到 `done_bool` 和部分 `active_mask` 用于上下文构造 | 需要继续核查 |
| parameter sharing | 同构 agent 常常共享 actor，critic 是否共享取决于实现；重点是输入语义要正确 | 当前是共享 actor / 共享 critic 方向，但 critic 输入语义还偏局部 | 方向可行，细节未对齐 |

## 总判断

如果按论文里的标准来讲，目前这版更准确的描述是：

- **分布式 actor + 带邻居上下文的 critic**

而不是严格意义上的：

- **MADDPG 式 centralized critic（joint obs + joint action）**
- **或 MAPPO 式 centralized value / shared observation critic**

所以现在更稳妥的表述不是“集中式 critic 没用”，而是：

- **我们已经尝试了让 critic 看更多多机信息**
- **但当前实现还没有完全对齐论文里更标准的 centralized critic 形式**
- **因此现阶段还不能据此下结论说 CTDE 这条线无效**

## 可以直接拿去汇报的一段话

对照 MADDPG 和 MAPPO 论文后，我觉得我们当前这版更像“给 critic 加了邻居上下文信息”，还不是标准意义上的 centralized critic。现在 actor 仍然是分布式的，这点没问题；但 critic 这边既没有显式使用 joint observation + joint action，也没有在 replay buffer 里完整保存这类多机联合 transition，所以还不能直接把目前结果理解为“集中式 critic 没有用”。更准确地说，是我们现在的 critic 改法可能还没有完全实现到论文里那种 CTDE 形式，因此下一步更值得先核查和补齐这些关键细节。

## 最小改动清单

这一轮不追求一步做成完整 MADDPG / MAPPO，只做最可能影响结果判断的最小修补。

### 优先级 1：先把 critic 到底看什么说清楚

目标：

- 明确当前 critic 是 `本机 state + 邻居 context + 本机 action`
- 不再把它表述成标准 joint-action centralized critic

动作：

1. 统一实验记录和后续表述  
   在文档和汇报里明确：
   - 当前版本是 context critic
   - 不是标准 MADDPG 式 joint critic

意义：

- 避免后面继续拿“当前结果”直接判断 centralized critic 有无效

### 优先级 2：补 replay buffer 的多机信息

目标：

- 让 critic 训练时能访问真正的多机 transition，而不只是当前 agent 样本

建议最小补法：

1. 在 buffer 中额外保存：
   - 所有 agent 当前 obs
   - 所有 agent 当前 action
   - 所有 agent 下一时刻 obs
   - active mask / done mask

2. 即使第一版不立刻全用上，也先把数据结构补齐

意义：

- 这是后面做 joint critic 或更标准 centralized critic 的前提
- 也是老师点名提到最可疑的地方

### 优先级 3：把 critic 输入改到更接近 joint 输入

目标：

- 不再只给 critic 喂“本机 action”
- 至少让 critic 能显式感知其他 agent 动作

建议最小补法：

1. 先做一个简化 joint 版本：
   - 当前 agent local state
   - 邻居/其他 agent 的 obs 或压缩后的共享信息
   - 当前 agent action
   - 其他 agent action

2. 如果完整 joint obs 太大，可以先保留局部邻居筛选，但动作输入要显式区分：
   - self action
   - neighbor actions

意义：

- 这是当前实现和 MADDPG 差别最大的地方
- 也是最可能决定“critic 到底有没有真的变强”的关键

### 优先级 4：明确 actor update 时其他 agent 动作的处理方式

目标：

- 回答老师那句“其他智能体 actor 是不是需要 detach”

建议最小补法：

1. 如果采用 joint action critic：
   - 更新当前 agent actor 时
   - 当前 agent action 保留梯度
   - 其他 agent action 作为固定背景输入 critic
   - 默认 detach

2. 如果仍是共享 actor：
   - 也要在实现上显式控制，只让“当前更新目标 agent 的动作分支”传梯度

意义：

- 这是标准 MADDPG 训练逻辑里的关键实现点
- 现在我们这版还没有真正碰到这个问题，因为结构上还不是 joint action critic

### 优先级 5：补 mask 核查，不让失活 agent 污染 critic

目标：

- 避免已经完成、碰撞、超时或 inactive 的 agent 继续污染 centralized input

建议最小补法：

1. 检查并统一：
   - replay 存储时的 active mask
   - critic target 计算时的 mask
   - actor loss / critic loss 统计时的 mask

2. 特别注意：
   - next-state centralized input 中是否混入已结束 agent 的无效信息

意义：

- MAPPO 类实现里这块通常很重要
- 多车导航里也很容易在这里埋偏差

## 建议执行顺序

最省时间的顺序建议是：

1. **先补 buffer 结构**
2. **再改 critic 输入形式**
3. **再处理 actor update 时其他 agent action 的 detach**
4. **最后补 mask 核查**

原因：

- buffer 和 critic 输入是结构性前提
- detach 问题只有在 joint action 真正进 critic 后才有意义
- mask 是必须补的收尾项，但不是最先卡住我们的地方

## 这一轮最值得做的一个小实验

如果只允许做一个最小验证实验，我建议是：

- **补 joint/multi-agent replay 信息**
- **让 critic 显式看到其他 agent action**
- **更新当前 agent actor 时把其他 agent action detach**

然后做一个短训练对比：

- 和当前 context critic 版比
- 只看训练稳定性和 actor 解冻后的退化幅度

不需要一开始就追求最终最优成绩，先看：

- critic 改法是否更符合 CTDE
- actor 解冻后是否没那么容易被错误梯度带跑

## 当前代码进展

目前已经完成两步最小实现：

1. `ReplayBuffer` 已经额外保存多机 transition 信息：
   - `joint_states`
   - `joint_actions`
   - `joint_next_states`
   - `active_mask`
   - `next_active_mask`
   - `agent_index`

2. `train_local_critic()` 已支持可选的 joint-action critic：
   - 新增开关：`DRL_MULTI_USE_JOINT_ACTION_CRITIC=1`
   - 开启后 critic 动作输入维度会扩成 `num_agents * action_dim`
   - actor 更新当前样本时：
     - 当前 agent 动作来自当前 actor
     - 其他 agent 动作来自 replay buffer
     - 等价于默认把其他 agent 动作当固定背景

兼容性说明：

- 旧 checkpoint 如果 critic 动作维度不匹配，会只恢复 actor，不强行恢复旧 critic

## 推荐的最小验证实验

当前最建议跑的不是大规模重训，而是一个短验证：

- 场景：`stage3_asym_three_5`
- warm start：`stage3_asym_pair_5_from_5a_best`
- critic：`local critic + joint-action critic`
- warm start 模式：`actor only`
- 目标：只看 actor 解冻后是否仍快速退化

对应脚本：

- [scripts/start_training_detached_multi_stage3_asym_three_5_joint_action_critic.sh](/home/jiutian/Local-Critic-Multi-Robot-Navigation/scripts/start_training_detached_multi_stage3_asym_three_5_joint_action_critic.sh)

这个脚本默认：

- `DRL_MULTI_USE_LOCAL_CRITIC=1`
- `DRL_MULTI_USE_JOINT_ACTION_CRITIC=1`
- `DRL_MULTI_LOAD_ACTOR_ONLY=1`
- `DRL_MULTI_MAX_EPOCHS=2`
- `DRL_MULTI_EVAL_EPISODES=24`

如果这组短实验比旧版 context critic 更稳，再决定是否继续放大验证。

## 下一步

1. 继续补一轮更细的代码核查：
   - active mask / done mask 是否足够
   - 训练时 neighbor action 用的是当前动作、target 动作，还是混合了不一致信息

2. 整理一份更明确的“如果要对齐 MADDPG，代码上最小需要改什么”
   - buffer 该多存什么
   - critic 输入该怎么改
   - actor 更新时其他 agent 动作该怎么固定/detach

3. 再决定是：
   - 先做一次“真正 joint critic”小改版
   - 还是先把当前 context critic 的细节补齐后再比较
