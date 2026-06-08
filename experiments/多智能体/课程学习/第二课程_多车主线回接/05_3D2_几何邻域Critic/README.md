# 05 3D2：几何邻域 Critic

作用：从课程 3A guarded best 接到 3车 D2 组，即几何邻域 critic。

D2 的含义：

- D2 是方法名，表示几何邻域 Critic。
- 旧3D2 和课程3D2 都是 D2。
- 区别在初始化路径：旧3D2 从旧统一 baseline 来，课程3D2 从课程 3A guarded actor 来。

当前结论：

- 训练 epoch 3 的 40 集 eval full success 为 `0.925`。
- 后续 latest 明显退化，epoch 17 full success 降到 `0.075`。
- epoch 3 best 的 300 集正式测试完成，full success 为 `0.830`。
- 课程3D2 和旧3D2 基本打平：课程3D2 full success 略高，但 timeout 更多。

## 300 集测试

- model: `TD3_velodyne_multi_v4_curriculum_stage2_to_3d2_geo_critic_from_3a_guarded_best`
- log: `logs/test/test_multi_stage2_three_geo_critic_best_TD3_velodyne_multi_v4_curriculum_stage2_to_3d2_geo_critic_from_3a_guarded_best_detached_20260608_084901.log`
- episodes: `300`
- agent success: `845 / 900 = 0.939`
- agent collision: `41 / 900 = 0.046`
- agent unresolved: `15 / 900 = 0.017`
- full success: `249 / 300 = 0.830`
- timeout episodes: `16 / 300 = 0.053`
- success hist `[0, 4, 47, 249]`
- collision hist `[262, 35, 3, 0]`

## 和三车对照

| model | agent success | collision | full success | timeout | 备注 |
| --- | ---: | ---: | ---: | ---: | --- |
| 旧 3A | `0.926` | `0.056` | `0.797` | `0.053` | 旧共享 policy |
| 旧 3D | `0.913` | `0.052` | `0.747` | `0.100` | 旧原始局部 critic |
| 旧 3D2 | `0.937` | `0.053` | `0.827` | `0.010` | 旧几何邻域 critic |
| 课程 3A | `0.939` | `0.043` | `0.827` | `0.060` | 课程 3A guarded best |
| 课程 3D | `0.930` | `0.049` | `0.813` | `0.070` | best 在解冻前 |
| 课程 3D2 | `0.939` | `0.046` | `0.830` | `0.053` | 当前最好普通三车节点，但优势很小 |

判断：

- 课程3D2 是目前普通三车标准测试里 full success 最高的一档，但只比旧3D2 高 `0.003`，不能夸大。
- 相比课程3A，课程3D2 full success 也只高 `0.003`，collision 略高，timeout 略低。
- 训练 latest 明显退化，所以后续如果继续 D2，不能沿用当前训练方式硬训；要做 actor 更新保护或性能回滚。

命名：

- 方法组：3D2
- 中文名：课程 3车几何邻域 Critic
