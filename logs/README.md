# logs 说明

当前根目录只保留**正在看**或**需要直接对比**的日志。

## 当前该看什么

1. 当前正在跑的 `5A + 5D hard switch`
   - `test_std5_5A5D_HARD_20260713_155604.log`
   - `test_stage3_asym_three_5_5A5D_HARD_20260713_155604.log`

2. 当前最重要的参考基线
   - `test_std5_PAIR_5D_20260713_084935.log`
   - `test_stage3_asym_three_5_PAIR_5D_20260713_104759.log`

3. 当前密集训练参考
   - `train_multi_curriculum_stage3_asym_three_5_detached_20260713_003642.log`

## 已归档

- `archive/20260713_invalid_resumed_runs/`
  - 这里放的是这次误续跑的无效日志
  - 原因：测试从 `episode 120` 继续跑，不是从 1 开始
  - 这些日志不再作为正式结果引用

## 简单约定

- 根目录：只放当前主线和关键基线
- `archive/`：放无效、被重跑覆盖、或阶段性淘汰的日志
