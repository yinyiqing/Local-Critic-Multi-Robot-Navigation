# 时空 Attention 主线

## 研究目标

在共享策略、局部观测和同场多机器人任务下，验证时空 Attention 是否能够学习其他车辆的相对运动和冲突趋势，从而提高个体成功率与整局完全成功率。

## 当前结构

```text
冻结 5D Actor
  + 每台机器人最近 6 帧 24 维本车观测
  + 激光扇区空间 Attention
  + 跨帧时间 Attention
  + 风险调制的门控残差动作
```

每帧观测由 20 维激光、目标距离/方向和上一步动作组成。执行阶段不读取其他机器人的 Gazebo 真值位置、目标或动作。

当前版本使用两个独立的 full-history MLP Q 网络。每个 Q 读取 `6 x 24` 的本车历史和当前动作。TD3 只训练 Attention 残差路径，基础 `5D` Actor 保持冻结。

## 当前文件

- `TD3/spatiotemporal_attention.py`
- `TD3/sequence_replay_buffer.py`
- `TD3/train_spatiotemporal_attention.py`
- `experiments/cases/attention_mixed_5.json`
- `scripts/start_training_detached_spatiotemporal_attention_5d.sh`
- `scripts/stop_training_detached_spatiotemporal_attention_5d.sh`

## 训练场景

`attention_mixed_5.json` 组合了三组五车场景：

- `standard`：普通随机导航。
- `pair`：以两车冲突为主、其余车辆构成背景交通。
- `three`：三车交叉、汇合或跟随交互。

其中交互场景分别定义在 `attention_pair_5.json` 和 `attention_three_5.json`。

ReplayBuffer 按三组均衡采样，避免训练数据被简单场景或单一冲突模式主导。

## 评价要求

所有实验至少报告 `success_rate`、`collision_rate`、`full_success_rate` 和 `timeout_rate`，并同时评价 standard 与交互场景。

所有对照必须使用相同场景、随机种子、回合数和指标口径。`full_success_rate` 是多机器人任务的核心指标，不能只根据个体平均成功率判断方法有效。

Attention 的必要对照为：

1. 冻结 `5D`，不加残差。
2. 冻结 `5D`，增加固定残差。
3. 冻结 `5D`，增加时空 Attention 残差。

只有第 3 项在相同场景与随机种子下稳定超过前两项，且输出随观测变化，才能认为增益来自多车时空信息，而不是固定减速或固定转向。

训练、停止和监控命令统一见 [根 README 的运行指南](../../README.md#运行指南)。
