# 时空 Attention 主线

## 研究目标

在共享策略、局部观测和同场多机器人任务下，验证时空 Attention 是否能够学习其他车辆的相对运动和冲突趋势，从而提高个体成功率与整局完全成功率。

## 当前结构

```text
阶段一：可训练的基础 Actor
  -> 学习到达、避障、提前减速和让行

阶段二：基础 Actor + 时空 Attention 联合微调
  -> 门控网络判断本车观测更接近 standard 还是 dense
  -> standard 主要使用基础动作
  -> dense 尽可能使用 Attention 动作
```

每帧观测由 20 维激光、目标距离/方向和上一步动作组成。执行阶段不读取其他机器人的 Gazebo 真值位置、目标或动作。

基础 Actor 使用旧 `5D` 权重初始化，但不冻结。第一阶段强制旁路 Attention，只更新基础 Actor。策略线速度范围为 `0.0 m/s` 到 `1.0 m/s`，不允许倒车，并通过局部激光安全速度塑形学习提前减速。

第二阶段启用时空 Attention。Attention 动作由基础动作 logits 和历史特征共同产生，零初始化保证阶段切换时与基础动作相同。门控使用 `standard=0`、`dense=1` 的场景标签监督训练，标签不会作为执行阶段输入。推理时门控只能根据本车六帧历史判断当前可观测环境复杂度。

当前版本使用两个独立的 full-history MLP Q 网络。每个 Q 读取 `6 x 24` 的本车历史和当前动作；Critic 不读取联合状态。

## 当前文件

- `TD3/spatiotemporal_attention.py`
- `TD3/sequence_replay_buffer.py`
- `TD3/train_spatiotemporal_attention.py`
- `experiments/cases/attention_mixed_5.json`
- `scripts/start_training_detached_spatiotemporal_attention_5d.sh`
- `scripts/stop_training_detached_spatiotemporal_attention_5d.sh`

## 训练场景

`attention_mixed_5.json` 只组合两组五车随机场景：

- `standard`：普通随机导航。
- `dense`：机器人和目标集中分布的复杂多车导航。

ReplayBuffer 按两组均衡采样。旧的 `pair` 和 `three` 固定场景不再进入训练、评估或门控监督。

## 评价要求

所有实验至少报告 `success_rate`、`collision_rate`、`full_success_rate` 和 `timeout_rate`，并同时评价 standard 与交互场景。

所有对照必须使用相同场景、随机种子、回合数和指标口径。`full_success_rate` 是多机器人任务的核心指标，不能只根据个体平均成功率判断方法有效。

Attention 的必要对照为：

1. 第一阶段保存的可训练基础 Actor。
2. 基础 Actor 加 Attention 动作，但使用固定门控。
3. 基础 Actor 加 Attention 动作和场景门控。

只有第 3 项在相同场景与随机种子下稳定超过前两项，且 `dense` 门控显著高于 `standard`，才能认为增益来自多车时空信息，而不是固定减速或固定转向。

训练、停止和监控命令统一见 [根 README 的运行指南](../../README.md#运行指南)。
