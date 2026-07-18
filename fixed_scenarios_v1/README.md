# Fixed Standard/Dense Scenarios v1

当前 Attention 主线的冻结五车场景数据。训练读取 `standard/train.json.gz` 和
`dense/train.json.gz`，验证读取对应的 `validation.json.gz`；环境与 manifest
读取逻辑位于活动工作区的 `TD3/` 和 `catkin_ws/`，不依赖此目录外的迁移副本。

| Pool | train | validation | test |
| --- | ---: | ---: | ---: |
| standard | 3000 | 500 | 1000 |
| dense | 6000 | 1000 | 2000 |

每条 manifest 固定五台车的 start、goal、heading 与四个 box。它们仅适用于当前
`TD3.world`、Pioneer3DX 碰撞尺寸、Velodyne 配置、模型名 `r1-r5` 和相同 reset
逻辑；不得在训练或验证时添加随机 jitter。

数据 SHA-256、生成 seed 与拒绝场景记录见
[data/fixed_v1/README.md](data/fixed_v1/README.md)。
