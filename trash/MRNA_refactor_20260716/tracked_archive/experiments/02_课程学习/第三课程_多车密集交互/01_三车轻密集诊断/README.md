# 01 三车轻密集诊断

作用：测试当前策略在轻度三车交错、靠近、目标汇合等 case 上的表现。

结论：

- 2D gentle best 测轻密集，整体碰撞高。
- 课程 3D2 best 测轻密集，整体仍然碰撞高。
- 说明 standard 普通三车接回来，不等于密集交互学会了。
- 后续不能直接把三车轻密集全量当训练入口，应先做三车过渡。

## 课程 3D2 best 诊断

- model: `TD3_velodyne_multi_v4_curriculum_stage2_to_3d2_geo_critic_from_3a_guarded_best`
- log: `logs/test/test_multi_curriculum_stage2b_three_light_dense_TD3_velodyne_multi_v4_curriculum_stage2_to_3d2_geo_critic_from_3a_guarded_best_detached_20260608_102113.log`
- episodes: `120`
- agent success: `162 / 360 = 0.450`
- agent collision: `197 / 360 = 0.547`
- agent unresolved: `2 / 360 = 0.006`
- full success: `21 / 120 = 0.175`
- timeout episodes: `2 / 120 = 0.017`
- success hist `[25, 49, 25, 21]`
- collision hist `[22, 23, 51, 24]`

分 case：

| case | success | collision | full success | timeout | 判断 |
| --- | ---: | ---: | ---: | ---: | --- |
| 三车目标汇合_轻聚集 | `0.883` | `0.133` | `0.700` | `0.000` | 基本会，但比普通场景更脆 |
| 三车轻对穿_横向留距 | `0.550` | `0.433` | `0.250` | `0.050` | 有部分能力，但碰撞高 |
| 三车靠墙会车_轻错位 | `0.533` | `0.450` | `0.100` | `0.050` | 不稳定 |
| 三车起点聚集_分散目标 | `0.367` | `0.633` | `0.000` | `0.000` | 失败 |
| 三车轻交叉_中心错位 | `0.200` | `0.800` | `0.000` | `0.000` | 失败 |
| 三车同向错峰_轻追越 | `0.167` | `0.833` | `0.000` | `0.000` | 失败 |

和 2D gentle best 的旧诊断相比：

| model | agent success | collision | full success | timeout |
| --- | ---: | ---: | ---: | ---: |
| 2D gentle best | `0.453` | `0.550` | `0.200` | `0.017` |
| 课程 3D2 best | `0.450` | `0.547` | `0.175` | `0.017` |

判断：

- 课程 3D2 在 standard 普通三车上是当前最高，但对轻密集几乎没有改善。
- 失败主要是碰撞，不是 timeout。
- 下一步应做三车过渡：两车有冲突，第三车轻参与，而不是直接训练这 6 个轻密集 case。
