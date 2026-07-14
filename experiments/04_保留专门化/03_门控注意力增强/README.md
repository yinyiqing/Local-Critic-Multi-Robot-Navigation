# 03 时空 Attention 残差主线

当前唯一的新训练主线是：

```text
冻结 5D Actor
  + 本车最近 6 帧观测
  + 激光扇区空间 Attention
  + 时间 Attention
  + 门控残差动作
```

它不再训练两个完整 Actor，也不再使用 hard switch。门控只控制残差修正强度，初始值接近零，因此训练起点等价于原始 `5D`。

## 输入与执行边界

- 每帧输入仍是本车 24 维观测。
- 空间 Attention 处理 20 个本车激光扇区。
- 时间 Attention 处理最近 6 帧。
- 不读取 Gazebo 中其他机器人的真实位置或动作。
- 训练和执行使用相同的本地可观测信息。

## 单一训练配置

- 冻结基础模型：`5D best`
- reward：基础 individual reward
- curriculum：`standard / dense` 混合采集
- dense 课程改为新的五车非对称强交互集，不再混入 `pair`
- ReplayBuffer：固定长度序列，按 `standard / dense = 1:1` 分层采样
- Critic：独立时空 Attention Twin Critic
- reward：进入 Critic target 前乘 `0.1`，降低终止奖励造成的 Q 梯度冲击
- Actor：Critic 预热后线性 warmup，再进行余弦学习率衰减
- Actor 约束：Q 项归一化；不再分别惩罚 gate 和 residual，只约束实际修正 `gate * residual`
- correction budget：修正超过最大 residual 的 `40%`（每维约 `0.1`）后才施加全局 hinge penalty
- standard 约束：直接惩罚 standard 样本上的实际修正，不把 dense residual 一起压零
- 稳定措施：TD3 target、delayed policy update、gradient clipping、无提升早停
- eval：固定随机种子；standard 固定 12 局；dense 每个 case 固定 4 局
- best：同时比较 `standard` 与 `dense`，优先提高两者中较差的 full success

默认新模型名为
`TD3_velodyne_multi_v5_attention_residual_from_5d_asym_dense_correction_v2`。它不会续接旧
`TD3_velodyne_multi_v5_attention_residual_from_5d_latest.pt`，因为 replay 格式、reward
尺度和优化目标已经不兼容；旧 checkpoint 和 best 文件仍保留用于对照。

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

新 correction v2 得到 best 后，需要在同一组固定种子、同一组 standard/dense case 上比较：

1. 冻结的原始 `5D`；
2. `5D + fixed residual`，固定值取自 Attention best 的全局均值；
3. `5D + Attention correction v2 best`。

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
- `experiments/02_课程学习/cases/stage3_asym_dense_full_5_cases.json`
- `experiments/02_课程学习/cases/stage4_spatiotemporal_attention_mixed_asym_dense_5_cases.json`

旧 Attention、联合动作 Critic 和 `5A + 5D` 双 Actor 只保留为历史结论，不复用其实现。
