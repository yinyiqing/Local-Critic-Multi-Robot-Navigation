# 10 智能体密集场景

本目录用于归档十车 dense case 测试结果。

## 当前状态

十车密集场景尚未开始。该设置可能对 reset、目标采样和仿真稳定性要求很高，应在三车和五车 dense case 后再推进。

## 注意事项

十车 dense case 不一定沿用三车默认 dense 参数。必要时需要通过环境变量调大采样范围或降低 clearance，例如：

```bash
DRL_MULTI_DENSE_START_X_RANGE=-3.0,3.0
DRL_MULTI_DENSE_START_Y_RANGE=-3.0,3.0
DRL_MULTI_DENSE_ROBOT_CLEARANCE=0.75
```
