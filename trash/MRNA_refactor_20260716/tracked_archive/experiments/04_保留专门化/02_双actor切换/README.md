# 02 双 Actor 切换

这里验证冻结两个 actor 后，简单切换能否利用二者的能力差异。

## 当前组合

- standard actor：`5A`
- dense actor：`5D`
- 两个 actor 都不更新

测试脚本支持：

- `single`：单 actor
- `hard_switch`：按最近邻距离和可见邻居数量切换
- `case_oracle`：按 case 名选择 actor，只用于估计上界

相关环境变量：

- `DRL_MULTI_STANDARD_ACTOR_FILE`
- `DRL_MULTI_DENSE_ACTOR_FILE`
- `DRL_MULTI_ACTOR_SELECTION_MODE`
- `DRL_MULTI_CASE_ORACLE_MAP`

## Hard Switch 结果

`5A + 5D -> stage3_asym_three_5`，120 episodes：

- `success_rate=0.893`
- `collision_rate=0.107`
- `unresolved_rate=0.002`
- `full_success_rate=0.583`
- `timeout_episode_rate=0.008`

它比 `PAIR(from_5d)` 略好，但没有超过单独使用 `5D`。

## Case Oracle 结果

结果文件：

- `oracle_maps/stage3_asym_three_5_5A_vs_5D_oracle.json`

三个 case 全部选择 `5D`。这说明 `5A` 没有提供稳定优于 `5D` 的 case 区域，二者的互补性不足。

## 当前结论

- 基于规则的整策略硬切换没有形成收益。
- `5A + 5D` 暂时不适合直接投入 learned gate 训练。
- 下一步应先找到分工更明确的专家，再评估门控。
- `hard_switch` 和 `case_oracle` 的通用实现继续保留，供新专家组合复用。
