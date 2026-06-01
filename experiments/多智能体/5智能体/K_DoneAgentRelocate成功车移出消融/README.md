# K. 五车 DoneAgentRelocate 成功车移出消融

本目录归档五车规模下的 test-only done-agent relocation 诊断实验。

## 方法定义

- 基础模型：`TD3_velodyne_multi_v4_individual_active_probe_5_best`
- 来源：J 组 Individual Active Probe epoch 3 best checkpoint
- 训练：不重新训练
- 测试阶段 reward：individual reward，仅用于统计
- 环境改动：开启 `DRL_MULTI_RELOCATE_SUCCESSFUL_DONE_AGENTS=1`
- 具体行为：某机器人成功到点后，本 step 统计完成，然后被移动到 `(20, 20)` 附近 holding area，不再作为场景内静态障碍
- 目的：验证“已成功机器人停在目标附近，物理阻挡后续机器人”是否是五车 full-success 长尾的主要瓶颈

## 300 Episodes 测试结果

| metric | value |
| --- | ---: |
| success_rate | 0.869 |
| collision_rate | 0.095 |
| unresolved_rate | 0.039 |
| full_success_rate | 0.533 |
| timeout_episode_rate | 0.167 |
| avg_reward | 101.268 |
| avg_env_steps | 71.007 |
| avg_agent_samples | 128.277 |
| avg_final_distance | 0.409 |

## 与 J 组原始测试对比

| metric | J Individual Active Probe | K DoneAgentRelocate | change |
| --- | ---: | ---: | ---: |
| success_rate | 0.869 | 0.869 | -0.001 |
| collision_rate | 0.087 | 0.095 | +0.007 |
| unresolved_rate | 0.045 | 0.039 | -0.006 |
| full_success_rate | 0.537 | 0.533 | -0.003 |
| timeout_episode_rate | 0.197 | 0.167 | -0.030 |
| avg_env_steps | 79.517 | 71.007 | -8.510 |
| avg_agent_samples | 137.693 | 128.277 | -9.417 |
| avg_final_distance | 0.414 | 0.409 | -0.005 |

## 当前结论

成功车移出场景后，timeout 从 59/300 降到 50/300，avg_env_steps 也下降，说明静态完成机器人确实会影响长尾完成效率。

但 full_success_rate 没有提升，反而从 `0.537` 微降到 `0.533`，collision_rate 也从 `0.087` 升到 `0.095`。因此，“成功车作为静态障碍”不是五车 full-success 低的主因。它是长尾 timeout 的一部分来源，但不是主要瓶颈。

当前更合理的判断是：五车问题仍然主要来自活跃机器人在复杂近障/会车局面中的局部策略缺陷，包括低速振荡、路径选择不稳定和碰撞权衡，而不是单纯由已成功机器人停住造成。

## 核心文件

- `五车DoneAgentRelocate/test_multi_individual_active_probe_5_best_relocate_done_detached_20260601_164040.raw.log.gz`
- `五车DoneAgentRelocate/test_multi_individual_active_probe_5_best_relocate_done_300episodes_clean.log`
- `五车DoneAgentRelocate/test_multi_individual_active_probe_5_best_relocate_done_300episodes.npy`
- `五车DoneAgentRelocate/test_multi_individual_active_probe_5_best_relocate_done_300episodes_summary.md`
