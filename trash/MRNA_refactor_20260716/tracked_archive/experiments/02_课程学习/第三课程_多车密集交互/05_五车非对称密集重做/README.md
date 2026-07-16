# 05 五车非对称密集重做

## 目的

旧的同步五车中心冲突过于对称，共享 policy 在局部观测、无通信条件下很容易让多车做出相似动作。因此当前课程改为：

1. 五车环境中的非对称双车主冲突：`stage3_asym_pair_5`
2. 五车环境中的弱三车交互：`stage3_asym_three_5`

当前主线只保留 `5D -> PAIR(from_5d) -> THREE_5`。

## `5D -> PAIR(from_5d)`

`5D` 作为 actor-only warm start，在 `stage3_asym_pair_5` 训练 3 epoch：

| epoch | success | collision | full success |
| --- | ---: | ---: | ---: |
| 1 | 0.900 | 0.104 | 0.729 |
| 2 | 0.912 | 0.087 | 0.729 |
| 3 | 0.921 | 0.079 | 0.750 |

训练日志已归档到：

- `experiments/04_保留专门化/01_冲突验证/logs/train/train_multi_curriculum_stage3_asym_pair_5_detached_20260712_234835.log`

正式测试：

| 场景 | success | collision | full success | timeout |
| --- | ---: | ---: | ---: | ---: |
| `standard_5` | 0.891 | 0.085 | 0.573 | 0.107 |
| `stage3_asym_three_5` | 0.880 | 0.122 | 0.575 | 0.000 |

结论：训练链路健康，但正式 dense 测试没有超过 `5D`。

## `PAIR(from_5d) -> THREE_5`

继续在 `stage3_asym_three_5` 训练 3 epoch：

| epoch | success | collision | full success | timeout |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.883 | 0.113 | 0.625 | 0.021 |
| 2 | 0.854 | 0.142 | 0.438 | 0.021 |
| 3 | 0.812 | 0.163 | 0.375 | 0.104 |

日志：

- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260713_003642.log`

结论：best 在第一轮，继续更新 actor 后再次退化。

## 当前判断

- 非对称 pair 课程比同步强对称 dense 起点更容易训练。
- `5D` 是合理的 pair warm start。
- 从 pair 继续覆盖训练同一个 actor，仍不能稳定获得更强的三车交互能力。
- 当前不再沿单 actor overwrite 路线继续扫解冻时间、更新频率或 anchor。
- 后续应先寻找真正互补的专家，再考虑冻结专家和训练门控。
