# 时空 Attention 主线

## 研究目标

在共享策略、局部观测和同场多机器人任务下，验证时空 Attention 是否能够学习其他车辆的相对运动和冲突趋势，从而提高个体成功率与整局完全成功率。

## 当前结构

```text
阶段一：可训练的基础 Actor
  -> 学习到达、避障、提前减速和让行

阶段二：冻结阶段一基础 Actor + 时空 Attention
  -> 门控网络预测本车当前是否存在可观测的交互风险
  -> 安全帧保持基础动作，近距接近和潜在会车时更多使用 Attention 动作
```

默认先积累 `20,000` 条 agent transition 仅训练 Critic；随后基础 Actor 在冻结 5D 动作锚定下开始更新，累计 `30,000` 条 transition 后保存并冻结基础 Actor，进入 Attention 阶段。Attention 启动后的前 `10,000` 条样本仅训练 Attention 与 gate，难例采样随后启用。基础分支在阶段二保持冻结，因此性能增益可以归因于 Attention，而不是基础动作继续漂移。可通过 `DRL_ATTENTION_ACTOR_START_STEP`、`DRL_ATTENTION_START_STEP` 和 `DRL_ATTENTION_BASE_WARMUP_STEPS` 调整。训练输出名固定为 `TD3_velodyne_multi_fixed_manifest_attention`，不接受版本化名称；后续迭代只修改这条训练主线，不新增启动脚本。

每帧观测由 20 维激光、目标距离/方向和上一步动作组成。执行阶段不读取其他机器人的 Gazebo 真值位置、目标或动作。

基础 Actor 使用旧 `5D` 权重初始化，但不冻结。第一阶段强制旁路 Attention，只更新基础 Actor。策略线速度范围为 `0.0 m/s` 到 `1.0 m/s`，不允许倒车，并通过局部激光安全速度塑形学习提前减速。

第二阶段启用时空 Attention。Attention 动作由基础动作 logits 和历史特征共同产生，零初始化保证阶段切换时与基础动作相同。gate 的初始概率、推理概率和 BCE 监督使用同一温度标定，避免低温把 Attention 的初始梯度压到近零。训练期使用可见活动车辆的距离、相对速度和 TTC 生成连续交互风险标签；这些 Gazebo 真值只用于监督 gate，不会输入 Actor。gate 分支仍屏蔽目标距离与方向，推理时只根据本车六帧激光与动作历史预测风险。低风险样本保持强动作校正约束，高风险样本允许 Attention 产生更明显的减速和让行校正。

当前版本使用两个独立的 full-history MLP Q 网络。每个 Q 读取 `6 x 24` 的本车历史和当前动作；Critic 不读取联合状态。

## 当前文件

- `TD3/spatiotemporal_attention.py`
- `TD3/sequence_replay_buffer.py`
- `TD3/train_spatiotemporal_attention.py`
- `TD3/scenario_manifests.py`
- `fixed_scenarios_v1/data/fixed_v1/`
- `scripts/start_training_detached_spatiotemporal_attention_5d.sh`
- `scripts/stop_training_detached_spatiotemporal_attention_5d.sh`

## 训练场景

当前主线只使用冻结的两组五车场景：

- `standard`：起点采样半宽固定为 `4.5 m`，单车目标直线距离为 `0.8-3.5 m`。
- `dense`：起点采样半宽为 `1.65-1.75 m`，单车目标直线距离为 `0.9-2.3 m`，车辆冲突显著更多。

训练集包含 3000 个 standard 和 6000 个 dense 场景，环境始终保持两组总采样权重 1:1，ReplayBuffer 也按两组均衡采样。Attention warmup 后，发生碰撞、超时或未全体完成的场景会在各组内部提高采样权重，同时保留 30% 均匀采样以避免过拟合少量失败案例。周期评估使用独立 validation split，并从文件开头按固定 `scenario_id` 顺序循环。旧的 `pair` 和 `three` 场景不再进入训练、评估或门控监督。

训练奖励新增小幅团队完成进度和全体完成奖励，并在训练期对近距离机器人施加风险惩罚。Actor 输入没有增加其他车辆真值，因此执行仍是无通信、分散式决策。

每个 manifest 固定五台车的 start、goal、heading 和四个 boxes，reset 不再添加随机抖动。训练 checkpoint 只记录数据集 ID，不记录服务器绝对路径。训练开始时会先评估冻结 5D Actor；进入 Attention 阶段后的首次验证会额外评估冻结的阶段一基础分支。Attention checkpoint 必须同时超过这两个对照和此前 Attention 最优值，不能把基础 Actor 的持续训练误判为 Attention 增益。

## 评价要求

所有实验至少报告 `success_rate`、`collision_rate`、`full_success_rate` 和 `timeout_rate`，并同时评价 standard 与 dense 场景。

所有对照必须使用相同场景、随机种子、回合数和指标口径。`full_success_rate` 是多机器人任务的核心指标，不能只根据个体平均成功率判断方法有效。

Attention 的必要对照为：

1. 第一阶段保存的可训练基础 Actor。
2. 基础 Actor 加 Attention 动作，但使用固定门控。
3. 基础 Actor 加 Attention 动作和交互风险门控。

只有第 3 项在相同场景与随机种子下稳定超过前两项，且高交互风险帧的 gate 显著高于低风险帧，才能认为增益来自多车时空信息，而不是固定减速或固定转向。

`TD3/evaluate_spatiotemporal_attention.py` 固化了这组对照。它在同一 validation manifest 上依次评估冻结 `5D`、阶段一基础 Actor、最终模型的基础分支、Attention 固定全开（`fixed_gate=1.0`）和完整学习门控模型，并将任务指标、门控/动作校正统计及 gate 与训练期交互风险标签的相关性写入 `TD3/results/attention_ablation_*.json`。运行该程序前必须准备与训练相同的 ROS/Gazebo 环境和五车 launch 文件。

主线默认从新配置开始训练，避免误续训旧门控标定或场景组标签 checkpoint。只有续训同一份 `causal_interaction_risk_gated` checkpoint 时才设置 `DRL_ATTENTION_RESUME=1`。

训练、停止和监控命令统一见 [根 README 的运行指南](../../README.md#运行指南)。
