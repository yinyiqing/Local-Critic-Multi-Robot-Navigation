# Fixed Random Scenarios v1

冻结日期：2026-07-17。所有场景在任何 Actor 或 gate 正式运行前完成筛选和冻结。

| Pool | train | validation | test | Master seed |
| --- | ---: | ---: | ---: | ---: |
| standard | 3000 | 500 | 1000 | 20260717 |
| dense | 6000 | 1000 | 2000 | 20260718 |

生成时为每个 split 预留 20% 候选。Gazebo 有效性检查结果：

- standard：5400 个候选中 5399 个通过，1 个 train 候选因 `r2` 初始激光 `0.325 m < 0.35 m` 被拒绝。
- dense：10800 个候选全部通过。
- 筛选只检查传感器、初始碰撞、初始终止和复位位置误差，没有加载 Actor。
- 通过后按原始顺序截取目标数量，没有按冲突指标或策略表现挑选。

每个 `.json.gz` 可直接设置为 `DRL_MULTI_MANIFEST_PATH`。训练使用 `random` sampling，验证和测试使用 `cycle`。

## SHA-256

```text
1cb612513f11fa1a38750fc59b1474c80f4746607d59ef54a73485e2141ff394  standard/train.json.gz
eb5061d6b61c1c3d57174f09308bf8c3f35c4b9d1cf8cc5971f003dd69ff3bb2  standard/validation.json.gz
699bc7237debadecb59400adafc075f20a4cc1fe5642ba82b74196d221ab35f8  standard/test.json.gz
d2a09cf8d51b89a366d3661487471d2383ef6ef4490133ab0efd6c59772f9a23  dense/train.json.gz
2d1dde389f927b924fa5993c47460bc60bac42aa9506ae3869c3139c9d1264b7  dense/validation.json.gz
03a744048102d7310db026e399e41c4ce664ed31b180438b2a2b519c78133eab  dense/test.json.gz
```

拒绝报告保存在对应 pool 的 `rejected_*.json` 中。候选全集可由固定 seed 和生成器重新生成，不纳入 Git。

完整性审计：

```bash
python scripts/audit_fixed_scenarios.py \
  experiments/04_保留专门化/05_论文主线/datasets/fixed_v1/{standard,dense}/{train,validation,test}.json.gz
```
