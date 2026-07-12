# 02 双actor切换

这一步现在定位成一个中间验证，不再当最终主线。

- 普通 actor
- 密集 actor
- 简单切换规则

第一版先追求清楚可跑，不追求花哨。

后面这里主要放：

- 选用的两个 actor
- 切换指标
- 切换规则
- 和单一 actor 的对比结果

一句话：

先验证“能力偏向存在”之后，直接做粗粒度策略切换够不够。

## 当前最小版本

- 普通 actor：
  - `5A`
- 密集 actor：
  - `PAIR`
- 切换规则：
  - 默认用 `5A`
  - 当前方可见邻居足够近时，切到 `PAIR`
  - 邻居重新变远后，再切回 `5A`

## 当前简单记录

- `2026-07-12`：已在测试脚本里补上最小双 actor 切换骨架，先做推理阶段切换，不动训练。
- `2026-07-12`：`DUAL -> 标准五车` 跑完，能跑通，但暂时没有超过 `5A`，说明切换规则还需要继续调。

## 第一轮结果

### `DUAL -> 标准五车`

- 120 episodes
- `success_rate=0.882`
- `collision_rate=0.102`
- `unresolved_rate=0.018`
- `full_success_rate=0.558`
- `timeout_episode_rate=0.092`
- `mean_dense_action_share=0.124`

### 当前一句话判断

- 这版最小双 actor 没有崩
- 但在标准五车上还没有超过 `5A`
- 需要结合 `DUAL -> dense` 一起判断

### `DUAL -> stage3_asym_three_5`

- 120 episodes
- `success_rate=0.867`
- `collision_rate=0.132`
- `unresolved_rate=0.002`
- `full_success_rate=0.550`
- `timeout_episode_rate=0.008`
- `mean_dense_action_share=0.392`

### 第一轮总判断

- 这版最小双 actor 能跑通
- 但无论在标准五车还是 dense，都没有超过当前单 actor 最优基线
- 所以现在不能说“双 actor 已经成功”
- 更准确地说：
  - 能力偏向确实存在
  - 但“整策略硬切换”太粗，还没有把两个 actor 的能力真正用好

### 下一步更合理的方向

- 不继续细调这版硬切换
- 这一步的价值主要是：
  - 证明问题不只是“要不要两个 actor”
  - 而是“如何识别交互状态、如何只在必要时增强交互建模”
- 下一步主线收敛到：
  - 局部交互感知
  - 轻量门控
  - 注意力增强
