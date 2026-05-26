# 密集场景验证

本目录用于归档机器人更密集时的验证结果。

密集场景仍保持“每个机器人有各自目标”的任务设定，只缩小起点和目标点的随机范围，让机器人在更小空间内到达各自目标，从而增加共享空间避让和局部交互压力。

## 当前计划

优先补三车 dense case：

| 编号 | 方法 | 目的 |
| --- | --- | --- |
| A | 共享 Policy Baseline | 基础对照 |
| C | Weighted08 | 强 reward shaping 对照 |
| D2 | 几何邻域 Critic + Weighted08 | 当前表现较好的 critic 结构 |

当前已扩展到 `5智能体/`。五车 dense baseline 和 D2 已完成直接对照。

## 运行入口

```bash
bash scripts/start_test_detached_multi_dense_baseline_3_best.sh
bash scripts/start_test_detached_multi_dense_weighted08_3_best.sh
bash scripts/start_test_detached_multi_dense_local_critic_geo_3_best.sh
bash scripts/start_test_detached_multi_dense_baseline_5_best.sh
bash scripts/start_test_detached_multi_dense_local_critic_geo_5_best.sh
```

对应停止脚本：

```bash
bash scripts/stop_test_detached_multi_dense_baseline_3_best.sh
bash scripts/stop_test_detached_multi_dense_weighted08_3_best.sh
bash scripts/stop_test_detached_multi_dense_local_critic_geo_3_best.sh
bash scripts/stop_test_detached_multi_dense_baseline_5_best.sh
bash scripts/stop_test_detached_multi_dense_local_critic_geo_5_best.sh
```
