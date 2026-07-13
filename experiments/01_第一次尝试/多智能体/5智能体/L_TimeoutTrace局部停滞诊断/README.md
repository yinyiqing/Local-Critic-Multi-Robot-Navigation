# L. 五车 TimeoutTrace 局部停滞诊断

本目录归档五车规模下针对 timeout 长尾的失败轨迹诊断。

## 方法定义

- 基础模型：`TD3_velodyne_multi_v4_individual_active_probe_5_best`
- 来源：J 组 Individual Active Probe epoch 3 best checkpoint
- 训练：不重新训练
- 测试阶段 reward：individual reward，仅用于统计
- 当时使用一次性测试封装和 trace 实现运行；二者均已在代码精简中删除，以下参数仅用于记录历史配置，当前代码不再接受这些开关
- 历史 trace 设置：
  - `DRL_MULTI_TRACE_FAILURES=1`
  - `DRL_MULTI_TRACE_FAILURE_MODE=timeout`
  - `DRL_MULTI_TRACE_WINDOW_STEPS=100`
- 目的：记录 timeout episode 末尾 100 step 中每辆车的动作、progress、min_laser、nearest_robot_distance 和目标相对角，判断长尾失败是被已完成机器人挡住、被其他活动机器人堵住，还是局部策略自身陷入停滞。

该运行原计划 120 episodes。由于前 42 episodes 已收集到 11 个 timeout trace，样本足够判断失败形态，因此手动停止；最后日志中的 `rospy shutdown` 来自停止过程，不代表测试自然崩溃。

## 42 Episodes 运行结果

| metric | value |
| --- | ---: |
| episodes | 42 |
| success_rate | 0.876 |
| collision_rate | 0.071 |
| unresolved_rate | 0.057 |
| full_success_rate | 0.548 |
| timeout_episode_rate | 0.262 |
| timeout_episodes | 11 |
| avg_reward | 103.553 |
| avg_env_steps | 95.976 |
| avg_agent_samples | 155.286 |
| avg_final_distance | 0.418 |

该结果不是新的 300 episodes benchmark，只用于失败机理诊断。

## Timeout Trace 聚合

11 个 timeout episode 共包含 12 条 unresolved-agent 末尾轨迹。聚合统计如下：

| metric | value |
| --- | ---: |
| trace_files | 11 |
| unresolved_agent_traces | 12 |
| `linear_mean < 0.02` | 12 / 12 |
| `linear < 0.05` step ratio | 1.000 |
| `abs(progress_sum) < 0.05` | 12 / 12 |
| `min_laser_mean < 0.8` | 11 / 12 |
| `nearest_robot_min > 1.2` | 11 / 12 |
| progress_sum mean | -0.001 |
| linear_mean mean | 0.0007 |
| abs_angular_mean mean | 0.346 |
| min_laser_mean mean | 0.618 |
| nearest_robot_mean mean | 2.886 |
| abs_theta_mean mean | 0.216 |
| final_distance mean | 1.999 |

## 关键样例

Episode 4 中有两辆 unresolved 车：

| agent | final_distance | progress_sum | linear_mean | abs_angular_mean | min_laser_mean | nearest_robot_mean | abs_theta_mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r1 | 2.502 | -0.008 | 0.0000 | 0.356 | 0.633 | 4.691 | 0.086 |
| r4 | 1.717 | 0.007 | 0.0012 | 0.315 | 0.613 | 2.015 | 0.294 |

这两辆车都不是被别的车贴身堵住，而是在近障状态下几乎不给线速度，只给角速度，最终没有距离进展。

## 当前结论

这组 trace 与 RViz 中观察到的“有 1 辆或多辆车完全静止或极小范围左右摆动，最终超时”一致，而且把问题定量化了：timeout 里的 unresolved 车不是整体五车协同失败，而是末尾一两辆车进入局部停滞吸引子。

更具体地说：

- 未完成车最后 100 step 几乎全部线速度为 0，`linear_mean` 全部小于 `0.02`。
- 同一窗口内 `progress_sum` 全部接近 0，说明不是绕远路，而是真的没有推进。
- 绝大多数 case 的 `nearest_robot_min > 1.2m`，说明不是直接被其他机器人贴身堵死。
- 绝大多数 case 的 `min_laser_mean < 0.8m`，说明策略通常处在近墙/近障状态。
- 角速度仍然存在，说明 actor 在做旋转/左右摆动，但没有逃离该状态。

因此，当前最可信的主因是：五车场景增加了进入近障复杂局面的概率，而现有局部 actor 在这些状态下学到的是“低线速度 + 旋转避障”的保守动作，缺少恢复推进能力。动态 reward 和局部 critic 可能没有显著改善协同能力，是因为主要瓶颈已经变成局部停滞/脱困能力，而不是单纯的邻居 reward credit assignment。

## 下一步建议

下一组应针对停滞机理做最小干预，而不是继续盲目调 cooperative reward：

- M 组：anti-stagnation reward ablation。仅在 `active`、未成功、未碰撞、近若干 step progress 很小且线速度很小时增加停滞惩罚；同时避免简单鼓励向障碍物硬冲。
- 同步记录 timeout trace，比较 `linear_mean`、`progress_sum`、`min_laser_mean` 和 `collision_rate` 是否变化。
- 如果 anti-stagnation 降低 timeout 但升高 collision，再考虑加上近障条件或转向恢复项，防止把“停住”直接改成“撞上去”。

## 核心文件

- `五车TimeoutTrace/test_multi_individual_active_probe_5_best_trace_timeout_detached_20260601_191138.raw.log.gz`
- `五车TimeoutTrace/test_multi_individual_active_probe_5_best_trace_timeout_42episodes.npy`
- `五车TimeoutTrace/failure_traces_summary.jsonl`
- `五车TimeoutTrace/failure_traces.tar.gz`
