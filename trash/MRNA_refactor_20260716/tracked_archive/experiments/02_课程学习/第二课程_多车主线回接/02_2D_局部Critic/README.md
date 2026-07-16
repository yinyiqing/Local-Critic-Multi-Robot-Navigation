# 02 2D：原始局部 Critic

作用：从课程 2A best 接到 2车 D 组，即原始局部邻域 critic。

结论：

- gentle 版是当前有效 2D 节点。
- 直接版和 guarded 版都已归入 `logs/failed/`，不作为主线。
- 这个阶段已经暴露出一个重要问题：早期 best 可以很好，但继续 actor 更新后容易退化。

命名：

- 方法组：2D
- 中文名：2车原始局部 Critic

