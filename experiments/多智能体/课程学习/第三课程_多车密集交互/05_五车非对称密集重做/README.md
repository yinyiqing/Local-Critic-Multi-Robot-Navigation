# 05 五车非对称密集重做

## 目的

这条分支不是继续硬训对称中心交叉，而是重做五车密集课程起点。

核心判断是：前面的密集课程之所以学不出来，主要问题不是 case 太少，而是起点过于对称。共享 policy 在局部观测、无通信条件下，容易让多辆车一起做出相似动作，直接冲向冲突区。

因此这里改成：

- 先在五车环境里训练非对称双车冲突
- 再过渡到五车环境里的弱非对称三车冲突
- 不把强对称中心交叉当作课程起点

## 当前记录

### 过渡探路

- `logs/superseded/train_multi_curriculum_stage2_pairwise_to_dense_detached_20260609_181829.log`

这是从旧思路过渡到“非对称重做”前的探路版本，不再作为当前口径。

### 五车非对称双车冲突

训练日志：

- `logs/train/train_multi_curriculum_stage3_asym_pair_5_detached_20260609_191500.log`

结果：

| epoch | success | collision | full success |
| --- | ---: | ---: | ---: |
| 1 | 0.912 | 0.083 | 0.729 |
| 2 | 0.912 | 0.087 | 0.729 |
| 3 | 0.883 | 0.113 | 0.646 |

结论：

- 这条非对称课程明显比 `dense_gentle` / `dense_bridge` 更健康
- 说明“过强对称性”确实是旧密集课程的重要问题
- 但仍然出现后期退化，best 仍在前两轮

### 五车非对称三车冲突

失败日志：

- `logs/failed/train_multi_curriculum_stage3_asym_three_5_detached_20260609_202710.log`

原因：

- 不是 case 错误
- 是 Gazebo/ROS 端口与上一轮训练残留进程冲突，`gzserver` 反复退出

当前有效训练日志：

- `logs/train/train_multi_curriculum_stage3_asym_three_5_detached_20260609_202936.log`

补充判断：

- 第一版 `stage3_asym_three_5` 虽然已经去掉强对称，但三车同时进入冲突区的程度仍然偏高
- 因此后续把第二级进一步改成“主冲突双车 + 第三车弱介入”的 softer 版本，再重新训练

## 当前结论

第三课程后续的重点不应是“必须先解决对称中心交叉”，而应是：

1. 先验证非对称密集课程能否学出稳定让行
2. 再决定是否需要进一步逼近对称强冲突

也就是说，对称 hardest case 更适合作为边界测试，而不是课程起点。
