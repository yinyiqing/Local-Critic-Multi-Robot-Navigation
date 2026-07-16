# MRNA 重构归档

归档日期：2026-07-16。

本目录保存 MRNA 分支重构时从活动工作区移出的旧研究。内容未直接删除，必要时可以按原相对路径恢复。

## 保留在活动工作区的内容

- 原始单智能体 TD3 baseline。
- 通用共享策略多智能体 TD3 baseline。
- 五车共享策略 baseline。
- 当前 Attention 依赖的冻结 `5D` baseline。
- 当前 v7 时空 Attention 实现和产物。
- ROS/Gazebo、Docker、容量检查和可视化基础设施。

## 归档结构

- `tracked_archive/`：旧实验文档、专用脚本、launch 文件和根目录旧资料。
- `local_artifacts/`：旧 checkpoint、模型、结果、TensorBoard 数据和缓存。该目录被 Git 忽略。

归档内容只用于恢复或追溯，不再作为当前主线入口。
