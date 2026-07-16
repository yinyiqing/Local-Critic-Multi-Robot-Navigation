# 03 时空 Attention 残差主线

当前唯一的新训练主线是：

```text
冻结 5D Actor
  + 本车最近 6 帧观测
  + 激光扇区空间 Attention
  + 时间 Attention
  + 门控残差动作
```

它不再训练两个完整 Actor，也不再使用 hard switch。门控只控制残差修正强度；v3
将初始 gate 设为 `0.2`，并把残差输出层初始化为零。因此训练起点严格等价于原始
`5D`，同时残差输出层能获得足够的首步策略梯度。

## 输入与执行边界

- 每帧输入仍是本车 24 维观测。
- 空间 Attention 处理 20 个本车激光扇区。
- 时间 Attention 处理最近 6 帧。
- 不读取 Gazebo 中其他机器人的真实位置或动作。
- 训练和执行使用相同的本地可观测信息。

## 单一训练配置

- 冻结基础模型：`5D best`
- reward：基础 individual reward
- curriculum：`standard / pair / three` 混合采集
- ReplayBuffer：固定长度序列，按 `standard / pair / three = 1:1:1` 分层采样；默认
  batch 为 `96`，三组样本充足时每组 `32`
- Critic：两个独立的轻量 full-history MLP Q 网络；每个 Q 读取最近 6 帧完整 24 维本车观测历史和当前动作，默认结构为 `146 -> 256 -> 256 -> 1`
- reward：进入 Critic target 前乘 `0.1`，降低终止奖励造成的 Q 梯度冲击
- Actor：Critic 预热后线性 warmup，再进行余弦学习率衰减
- Actor 约束：Q 项归一化；不单独惩罚 gate 和 residual，只约束实际修正量
  `gate * residual`
- 局部风险：只使用现有 6 帧激光中“1.5 米内且持续接近”这一项连续信号；实际
  correction 连续乘以 risk，风险为零时严格回到冻结 5D，不输入场景标签或增加离散切换
- 稳定措施：TD3 target、delayed policy update、gradient clipping、无提升早停
- eval：固定随机种子；standard 固定 `30` 局；three 每个 case 固定 `10` 局，共
  `30` 局
- best：同时比较 `standard` 与 `three`，优先提高两者中较差的 full success

默认新模型名为
`TD3_velodyne_multi_v5_attention_residual_from_5d_history_mlp_critic_v7`。它不会续接旧
`TD3_velodyne_multi_v5_attention_residual_from_5d_latest.pt` 或
`TD3_velodyne_multi_v5_attention_residual_from_5d_risk_modulated_v6_latest.pt`，因为 Critic
结构、replay/checkpoint 配置和优化目标已经不兼容；旧 checkpoint 和 best 文件仍保留用于对照。

当前先验证“保留双 Q、Actor 保留 Attention、Critic 改成两个独立轻量 MLP 并读取完整历史”
能否比 v6 更稳定。不加入让行 reward、停滞信号或邻居真值；只有这一轮失败后才逐项尝试。

## v3 阶段结论

`correction_gate_v3` 已证明 Gate 不再归零，并将 three full success 从冻结 5D 的
`40.0%` 提高到最高 `53.3%`；但对应 standard 从 `70.0%` 降到 `63.3%`。其约束按
`standard / dense` group 施加，与单车实际看到的局部风险不完全一致，因此 v4 改为
仅依赖可观测动态风险。v3 checkpoint 和日志保留作为对照，不再续训。

`observable_risk_v4` 尝试只惩罚低风险 correction。100 episode、9738 samples 后，
全 replay 上 risk 与 correction 的相关系数为 `-0.069`；约束梯度已经足够强，继续增加
权重只会压制 Actor，因此该策略停止。v5 改为让 Gate 以小权重回归同一连续风险目标。

`risk_aligned_gate_v5` 在 100 episode、10555 samples 后将 risk 与 Gate 的相关性提高到
`0.086`，但 residual 反向补偿，risk 与实际 correction 仍为 `-0.098`，因此不做性能
评估。v6 直接连续调制实际 correction，避免 Gate 与 residual 互相抵消。

`risk_modulated_v6` 是上一轮候选：在 100 episode、9542 samples 后，risk 与 effective Gate、实际
correction 的相关性分别达到 `0.9997` 和 `0.9962`；高风险 correction 约为低风险的
38 倍。固定种子评估结果为：standard success/full `94.0% / 73.3%`，three
success/full `86.7% / 53.3%`。它保持了 v3 的最高 three full，同时将 standard full
从 v3 best 的 `63.3%` 恢复到 `73.3%`。

v7 在 v6 基础上不改 Actor 风险调制路径，只把 Critic 从 Attention Critic 改为两个独立的
full-history MLP Q 网络。当前代码和启动脚本已经切到 v7，正式训练结果尚未归档。

## 旧 run 的波动诊断

2026-07-13 停止的旧 run 在约 670 episode、71889 samples 时出现了以下现象：

- best gate 约为 `0.947`，latest gate 约为 `0.995`，且样本间方差很小；
- best residual 近似常量 `[-0.249, -0.250]`；
- latest residual 近似常量 `[-0.250, +0.246]`，角速度修正发生翻转；
- 原 residual 正则最大只有约 `0.000625`，相对 `60-80` 量级 Actor loss 可忽略；
- Critic 裁剪前梯度从约 `1000` 增长到常见 `9000-10800`，最大约 `37405`；
- 旧 eval 每组仅 12 局，three case 又按权重随机抽取，测量噪声较大。

因此该 run 不能证明时空 Attention 学到了按场景变化的时空关系。现有证据更接近
“Attention 退化为全局动作偏置”，latest 波动则来自角速度偏置翻转和 Critic 持续漂移。

## 必做消融

新 v6 得到 best 后，需要在同一组固定种子、同一组 standard/three case 上比较：

1. 冻结的原始 `5D`；
2. `5D + fixed residual`，固定值取自 Attention best 的全局均值；
3. `5D + Attention v6 best`。

只有第 3 项稳定超过第 2 项，且 gate/residual 在不同 group 和样本间存在有效方差，
才能把增益归因于时空 Attention，而不是固定减速或转向偏置。

不启用旧 Local Critic、邻居 reward averaging、local-navigation reward、anti-stagnation、wall-clearance、Actor anchor 或双 Actor 选择器。

## 入口

```bash
bash scripts/start_training_detached_spatiotemporal_attention_5d.sh
bash scripts/stop_training_detached_spatiotemporal_attention_5d.sh
```

核心文件：

- `TD3/spatiotemporal_attention.py`
- `TD3/sequence_replay_buffer.py`
- `TD3/train_spatiotemporal_attention.py`
- `experiments/02_课程学习/cases/stage4_spatiotemporal_attention_mixed_5_cases.json`

旧 Attention、联合动作 Critic 和 `5A + 5D` 双 Actor 只保留为历史结论，不复用其实现。
