# 05 五车非对称密集重做

## 目的

这条分支不是继续硬训对称中心交叉，而是重做五车密集课程起点。

核心判断是：前面的密集课程之所以学不出来，主要问题不是 case 太少，而是起点过于对称。共享 policy 在局部观测、无通信条件下，容易让多辆车一起做出相似动作，直接冲向冲突区。

因此这里改成：

- 先在五车环境里训练非对称双车冲突
- 再过渡到五车环境里的弱非对称三车冲突
- 不把强对称中心交叉当作课程起点

## 当前记录

### 过渡探路

- `logs/superseded/train_multi_curriculum_stage2_pairwise_to_dense_detached_20260609_181829.log`

这是从旧思路过渡到“非对称重做”前的探路版本，不再作为当前口径。

### 五车非对称双车冲突

训练日志：

- `logs/train/train_multi_curriculum_stage3_asym_pair_5_detached_20260609_191500.log`

结果：

| epoch | success | collision | full success |
| --- | ---: | ---: | ---: |
| 1 | 0.912 | 0.083 | 0.729 |
| 2 | 0.912 | 0.087 | 0.729 |
| 3 | 0.883 | 0.113 | 0.646 |

结论：

- 这条非对称课程明显比 `dense_gentle` / `dense_bridge` 更健康
- 说明“过强对称性”确实是旧密集课程的重要问题
- 但仍然出现后期退化，best 仍在前两轮

补充记录：

- `2026-07-12`：准备补做 `5D -> stage3_asym_pair_5`
  - 目的不是重复旧 `5A -> PAIR`
  - 而是验证“带弱交互基础的普通 actor”作为 dense warm start 是否更合理
  - 由于 `5D` 当时带几何邻域 critic，而当前 `stage3_asym_pair_5` 默认不是同一 critic 结构，这次 warm start 默认采用 `actor-only`

### 五车非对称三车冲突

失败日志：

- `logs/failed/train_multi_curriculum_stage3_asym_three_5_detached_20260609_202710.log`

原因：

- 不是 case 错误
- 是 Gazebo/ROS 端口与上一轮训练残留进程冲突，`gzserver` 反复退出

当前有效训练日志：

- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260609_202936.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260609_210249.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260609_214533.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_090817.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_134006.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_153603.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_164119.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_191507.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_202722.log`
- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_223831.log`

补充测试日志：

- `logs/train/test_multi_curriculum_stage3_asym_three_5_TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5a_cleanstart_v2_best_detached_20260609_233731.log`

补充判断：

- 第一版 `stage3_asym_three_5` 虽然已经去掉强对称，但三车同时进入冲突区的程度仍然偏高
- 因此后续把第二级进一步改成“主冲突双车 + 第三车弱介入”的 softer 版本，再重新训练

后续两次实验结论：

- `20260609_210249`：
  - actor 长时间未解冻
  - 训练大部分时间仍在沿用旧策略
  - 说明这个版本无法判断第三课程是否真的学得动

- `20260609_214533`：
  - 提前解冻 actor 后，训练前段尚能维持 `2/5`、`3/5`
  - actor 解冻后很快退化为大量 `0/5`、`1/5`
  - `Eval Epoch 1` 下降到 success `0.021`、collision `0.787`、full success `0.000`
  - 说明当前主要问题已经不是 case 是否还不够非对称，而是 actor 在 `pair -> three` 阶段更新时快速退化

### 2026-06-10：解冻窗口对比

先做了一个干净的 warm-start 检查：

- `stage3_asym_pair_5_from_5a_cleanstart_v2_best` 直接测试 `stage3_asym_three_5`
- 结果说明 warm start actor 本身是可用的，不是“一上来就不适配新 case”

在这个前提下，对比了两组解冻窗口：

- `20260610_090817`，`delay=12000`
  - Epoch 1：success `0.904`，collision `0.096`，full success `0.646`
  - Epoch 2：success `0.871`，collision `0.125`，full success `0.583`
  - Epoch 3：success `0.887`，collision `0.117`，full success `0.583`
  - 结论：没有像 `delay=4000` 那样学炸，但也没有明显超过 warm start

- `20260610_134006`，`delay=8000`
  - Epoch 1：success `0.879`，collision `0.121`，full success `0.583`
  - Epoch 2：success `0.863`，collision `0.146`，full success `0.500`
  - Epoch 3：success `0.808`，collision `0.171`，full success `0.354`
  - 结论：比 `delay=12000` 更差，说明继续提前解冻只会加重退化

额外说明：

- `logs/failed/train_multi_curriculum_stage3_asym_three_5_detached_20260610_133924.log`
  - 这次不是算法结果
  - 是默认 ROS/Gazebo 端口和旧实例冲突，`gzserver` 启动失败
  - 已归为无效启动日志

- `logs/failed/train_multi_curriculum_stage3_asym_three_5_detached_20260610_191159.log`
  - 这次不是算法结果
  - 训练进程错误复用了默认端口，碰到旧 Gazebo 实例，出现 `entity already exists` 和 `gzserver` 反复重启

- `logs/failed/train_multi_curriculum_stage3_asym_three_5_detached_20260610_191320.log`
  - 这次不是算法结果
  - 虽然改了端口，但该端口本身已被旧 `gzserver` 占用，训练误判“已有 ROS master”，随后 `rospy.init_node` 失败

这一轮对比之后，可以把“继续扫 delay”基本收口：

- `22000`：太晚，基本不学
- `12000`：当前最稳，但只是“最不坏”
- `8000`：明显继续变差
- `4000`：容易直接学炸

因此第三课程下一步不再继续找“最佳解冻时间”，而是转去直接处理 actor 更新机制。

### 2026-06-10：主线切到 actor 更新机制

为了直接验证“critic 多更、actor 少更”是否能缓解退化，代码增加了：

- `DRL_MULTI_POLICY_FREQ`

这使得第三课程可以在保持 warm start 和 case 不变的前提下，单独降低 actor 更新频率。

继续沿着“actor 更新稳定性”主线，新增了两组实验：

- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_153603.log`
  - `delay=12000`
  - `policy_freq=6`
  - 目的是测试“actor 解冻后更少更新”能否比 `policy_freq=2` 更稳
  - 结果：
    - Epoch 1：success `0.875`，collision `0.125`，full success `0.562`
    - Epoch 2：success `0.892`，collision `0.108`，full success `0.604`
    - Epoch 3：success `0.867`，collision `0.133`，full success `0.542`
  - 结论：
    - 比 `delay=8000` 更稳
    - 但最终仍未优于 `delay=12000 + policy_freq=2` 的最好点
    - 说明“少更 actor”只能缓解，不能根治

- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_164119.log`
  - `delay=12000`
  - `policy_freq=6`
  - `actor_anchor_weight=0.05`
  - 目的是在 warm start actor 基础上，加一个轻量约束，避免 actor 一解冻就迅速偏离原有可用策略
  - 结果：
    - Epoch 1：success `0.867`，collision `0.133`，full success `0.604`
    - Epoch 2：success `0.900`，collision `0.092`，full success `0.646`
    - Epoch 3：success `0.850`，collision `0.142`，full success `0.521`
  - 结论：
    - 中期确实更好，`Epoch 2` 回到了目前第三课程的最好水平
    - 但到 `Epoch 3` 仍然回落
    - 说明 actor anchor 是有效缓解项，但还不足以彻底解决退化

- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_191507.log`
  - `delay=12000`
  - `policy_freq=6`
  - `actor_anchor_weight=0.1`
  - 目的是测试更强的 warm-start 约束能否进一步压住 actor 漂移
  - 结果：
    - Epoch 1：success `0.879`，collision `0.117`，full success `0.521`
    - Epoch 2：success `0.875`，collision `0.125`，full success `0.583`
    - Epoch 3：success `0.838`，collision `0.146`，full success `0.500`
  - 结论：
    - 比 `actor_anchor_weight=0.05` 更差
    - 说明继续单纯增大 actor anchor 不能解决问题，这条线可以基本收口

- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_202722.log`
  - `actor_update_delay_steps=999999`
  - `policy_freq=2`
  - `actor_anchor_weight=0`
  - 这版不是“继续想办法稳住解冻”，而是直接做关键对照：第三课程里 actor 全程冻结，只训练 critic
  - 结果：
    - Epoch 1：success `0.883`，collision `0.117`，full success `0.562`
    - Epoch 2：success `0.879`，collision `0.121`，full success `0.542`
    - Epoch 3：success `0.879`，collision `0.129`，full success `0.583`
  - 结论：
    - 明显比多种“解冻后退化”的版本更稳
    - 说明第三课程当前最主要的问题，确实是 actor 更新本身
    - 但“只训 critic、不动 actor”也没有显著超过最好的 warm-start 基线，因此它更像是在保住已有能力，而不是学到新的三车交互策略

- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260610_223831.log`
  - `actor_update_delay_steps=0`
  - `policy_freq=2`
  - `actor_anchor_weight=0`
  - 这版用于补齐一个之前真正没做过的关键对照：第三课程从第一步开始就解冻 actor
  - 结果：
    - Epoch 1：success `0.812`，collision `0.188`，full success `0.438`
    - Epoch 2：success `0.804`，collision `0.175`，full success `0.375`
    - Epoch 3：success `0.746`，collision `0.237`，full success `0.229`
  - 结论：
    - 这是目前第三课程中最差的一组有效结果
    - 说明“场景切换不算太大，所以 actor 应该从一开始就更新”这个猜想，在当前实现下并不成立
    - 当前第三课程里，actor 越早参与更新，越容易破坏已有策略

## 当前结论

第三课程后续的重点不应是“必须先解决对称中心交叉”，而应是：

1. 先验证非对称密集课程能否学出稳定让行
2. 再决定是否需要进一步逼近对称强冲突

也就是说，对称 hardest case 更适合作为边界测试，而不是课程起点。

## 当前下一步

第三课程的下一步不再是继续加难 case，也不再直接推进更强对称密集。

当前更准确的主线结论是：

1. `stage3_asym_pair_5 -> stage3_asym_three_5` 的 warm start 本身是可用的
2. 第三课程当前真正的破坏项是 actor 更新，而不是 case 文件本身
3. `delay`、`policy_freq`、轻量 `anchor` 都只能缓解，不能根治
4. actor 全冻结可以保住已有能力，但暂时没有带来明显的新收益
5. `delay=0 / 4000 / 8000 / 12000 / 22000 / 全冻结` 这一组对照已经基本把“解冻时机”这条线试清楚了，后续不应再继续在这里做零散盲调

因此第三课程下一步不应再继续做零散的“小修小补”，而应明确围绕下面二选一推进：

- 要么接受第三课程暂时不更新 actor，把它当成稳定过渡/评估阶段
- 要么重新设计更本质的 actor 更新方案，而不是继续微调解冻时机
