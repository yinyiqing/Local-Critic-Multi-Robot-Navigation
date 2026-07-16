# 01 冲突验证

这里验证单一 actor 继续向密集场景训练时，是否会破坏已有的普通导航能力。

## 当前模型

- 普通 actor：`5A`
  - `TD3_velodyne_multi_v4_curriculum_stage2_to_5a_shared_from_3d2_guarded_best`
- 桥接 actor：`5D`
  - `TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best`
- 密集专门化 actor：`PAIR(from_5d)`
  - `TD3_velodyne_multi_v4_curriculum_stage3_asym_pair_5_from_5d_best`

## 测试口径

- `standard_5`：普通场景主测试
- `stage3_asym_three_5`：dense 场景主测试
- `stage2_dense`：压力测试，不作为当前主 benchmark

## 正式结果

| 模型 | 场景 | success | collision | full success | timeout |
| --- | --- | ---: | ---: | ---: | ---: |
| `5A` | `standard_5` | 0.897 | 0.087 | 0.600 | 0.087 |
| `5A` | `stage3_asym_three_5` | 0.885 | 0.118 | 0.567 | 0.008 |
| `5D` | `standard_5` | 0.882 | 0.098 | 0.550 | 0.100 |
| `5D` | `stage3_asym_three_5` | 0.902 | 0.097 | 0.650 | 0.017 |
| `PAIR(from_5d)` | `standard_5` | 0.891 | 0.085 | 0.573 | 0.107 |
| `PAIR(from_5d)` | `stage3_asym_three_5` | 0.880 | 0.122 | 0.575 | 0.000 |

## 结论

- `5A` 仍是普通导航主干。
- `5D` 是当前正式 dense 测试最稳的 bridge baseline。
- `PAIR(from_5d)` 的训练内结果更顺，但正式 dense 测试没有超过 `5D`。
- 继续覆盖训练单一 actor 不能稳定同时提高普通能力和 dense 能力。
- 后续若做专家组合，应先验证专家互补性，再训练门控。

## 有效日志

- `logs/test_stage3_asym_three_5_5A_20260707_193554.log`
- `logs/test_stage3_asym_three_5_5D_20260707_213454.log`
- `logs/test_std5_5D_20260707_205700.log`
- `logs/train/train_multi_curriculum_stage3_asym_pair_5_detached_20260712_234835.log`
- `logs/test_std5_PAIR_5D_20260713_084935.log`
- `logs/test_stage3_asym_three_5_PAIR_5D_20260713_104759.log`
