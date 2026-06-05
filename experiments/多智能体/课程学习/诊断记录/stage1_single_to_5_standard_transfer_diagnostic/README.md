# Stage 1 单车补课到五车标准迁移诊断

## 口径

- 测试模型：`TD3_velodyne_multi_v4_curriculum_stage1_single_best`
- 训练来源：Stage 1 单车局部导航课程
- 测试场景：`standard`
- 机器人数量：5
- 执行方式：同一个 actor 复制给 5 辆车，每辆车只使用自身观测
- 原始运行产物：已清理，仅保留复盘摘要

## 结果

该测试原计划运行 300 episodes，但 RViz 中出现高频左右摆动，且前 9 个 episode 已经连续暴露失败模式，因此提前停止。

| 指标 | 数值 |
| --- | ---: |
| 已完成 episodes | 9 |
| success_rate | 0.644 |
| collision_rate | 0.200 |
| unresolved_rate | 0.200 |
| full_success_rate | 0.000 |
| timeout_episode_rate | 0.667 |
| avg_env_steps | 200.1 |

## 观察

- 9 个 episode 中没有一次五车全成功。
- 6 个 episode 跑满 300 step，和 RViz 中多车左右摆动、近目标停滞的现象一致。
- 单车课程 best 直接复制到五车后没有稳定迁移，说明 Stage 1 课程没有充分覆盖近目标捕获、侧墙干扰和多车压力下的局部振荡。

## 判断

Stage 1 targeted case 覆盖范围过窄。它能在少量单车 case 上取得较高成功率，但不足以判断基础局部导航缺陷已经解决。后续不应继续直接提高多车密集难度，应先补充更细的局部振荡课程。
