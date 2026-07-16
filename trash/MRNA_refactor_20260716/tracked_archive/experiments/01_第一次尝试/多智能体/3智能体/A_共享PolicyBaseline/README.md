# A. 三车共享 Policy Baseline

本目录用于保存三车共享 policy baseline 的训练与测试结果。共享 policy baseline 指多个机器人在同一环境中运行，并共同使用同一个 actor/critic 策略；执行阶段每个机器人仍只使用自身观测。

## 目录结构

- `三车共享PolicyBaseline/`
  - 当前三车主线实验的共享 policy baseline。
  - 所有三车对照实验均应与该组保持相同 warm-start 基准和测试设置。
  - 该组是后续 reward-only、weighted08 和局部邻域 Critic 对照的强 baseline。

## 当前三车 baseline 结果

三车共享 Policy Baseline 使用 `TD3_velodyne_multi_v4` 作为统一 warm-start 基准，best checkpoint 的 300 episodes 测试结果为：

| 指标 | 数值 |
| --- | ---: |
| `success_rate` | `0.926` |
| `collision_rate` | `0.056` |
| `full_success_rate` | `0.797` |
| `timeout_rate` | `0.053` |
| `avg_reward` | `119.580` |

详细记录见：

- `三车共享PolicyBaseline/test_multi_baseline_3_best_300episodes_summary.md`
- `三车共享PolicyBaseline/test_multi_baseline_3_best_300episodes_clean.log`
- `三车共享PolicyBaseline/train_multi_baseline_3_detached_20260520_171539.log`
