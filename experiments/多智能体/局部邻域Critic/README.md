# 局部邻域 Critic 实验目录

本目录用于归档局部邻域 Critic 方向的计划、日志和阶段结论。顶层保留面向阅读的文档，具体训练和测试日志按实验阶段放入子目录。

## 顶层文档

- `实验计划.md`：方法设计、实验阶段、对照设置和评价指标。
- `实验总结.md`：当前已完成实验的阶段总结，重点记录三车局部邻域 Critic 结果。
- `环境容量验证.md`：2/3/5/10 车环境容量检查结论。

## 子目录

- `容量验证/`：不同机器人数量下的 reset、goal 采样和随机运行检查日志。
- `两车单邻居验证/`：两车局部邻域 Critic 的训练与测试日志，用于验证 critic context、mask、checkpoint 和测试流程是否跑通。两车场景下每个机器人最多只有一个邻居，因此不用于验证多邻居排序。
- `三车多邻居验证/`：三车局部邻域 Critic 的正式小规模多邻居实验，包含训练日志、300 episodes clean 测试记录和测试摘要。

当前最重要的结果文件：

```text
三车多邻居验证/test_multi_local_critic_3_best_300episodes_summary.md
三车多邻居验证/test_multi_local_critic_3_best_300episodes_clean.log
```
