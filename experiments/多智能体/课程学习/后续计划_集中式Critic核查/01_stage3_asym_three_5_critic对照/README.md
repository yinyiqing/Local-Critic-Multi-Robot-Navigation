# 01 `stage3_asym_three_5` critic 对照

## 这一步在测什么

- 基础场景：五车 `stage3_asym_three_5`
- warm start：上一阶段可用 actor
- 训练长度：`2 epoch`
- 目的：只改 critic 形式，看看 actor 解冻后短期稳定性会不会不一样

## 两组设置

### 1. joint-action critic 组

- 脚本：
  - [scripts/start_training_detached_multi_stage3_asym_three_5_joint_action_critic.sh](/home/jiutian/Local-Critic-Multi-Robot-Navigation/scripts/start_training_detached_multi_stage3_asym_three_5_joint_action_critic.sh)
- 关键改动：
  - `DRL_MULTI_USE_JOINT_ACTION_CRITIC=1`
- 日志：
  - [train_multi_stage3_asym_three_5_joint_action_critic_detached_20260704_223140.log](/home/jiutian/Local-Critic-Multi-Robot-Navigation/experiments/多智能体/课程学习/后续计划_集中式Critic核查/01_stage3_asym_three_5_critic对照/logs/train_multi_stage3_asym_three_5_joint_action_critic_detached_20260704_223140.log)

### 2. context critic control 组

- 脚本：
  - [scripts/start_training_detached_multi_stage3_asym_three_5_context_critic_control.sh](/home/jiutian/Local-Critic-Multi-Robot-Navigation/scripts/start_training_detached_multi_stage3_asym_three_5_context_critic_control.sh)
- 关键改动：
  - `DRL_MULTI_USE_JOINT_ACTION_CRITIC=0`
- 日志：
  - [train_multi_stage3_asym_three_5_context_critic_control_detached_20260704_232939.log](/home/jiutian/Local-Critic-Multi-Robot-Navigation/experiments/多智能体/课程学习/后续计划_集中式Critic核查/01_stage3_asym_three_5_critic对照/logs/train_multi_stage3_asym_three_5_context_critic_control_detached_20260704_232939.log)

## 结果

| 组别 | success_rate | collision_rate | full_success_rate | avg_reward |
| --- | --- | --- | --- | --- |
| joint-action critic | 0.917 | 0.083 | 0.625 | 110.256 |
| context critic control | 0.833 | 0.167 | 0.417 | 90.102 |

## 当前结论

- 在这组公平短对照里，joint-action critic 明显好于旧的 context critic
- actor 解冻后没有出现“立刻崩掉”的老问题
- 这还不能说明问题已经彻底解决
- 但已经足够说明：critic 输入改法是值得继续查下去的主线

## 归档说明

- `logs/`：有效结果
- `invalid/`：中断、warm start 失败、环境残留导致无效的日志
