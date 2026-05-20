# 多智能体实验归档

多智能体相关实验统一放在这个目录下。这里主要保存实验说明、总结和关键日志归档；正式模型、checkpoint 和结果文件仍统一保存在 `TD3/` 下，避免影响训练和测试脚本。

## 目录

- `共享PolicyBaseline/`
  - 普通多智能体共享 policy baseline。
  - 这一版不包含动态 reward。
  - 对应模型名：`TD3_velodyne_multi_v4`

- `动态Reward/`
  - 在共享 policy baseline 基础上加入局部动态 reward。
  - 训练阶段使用雷达感知范围内机器人 reward 平均。
  - 测试阶段关闭动态 reward，用原始 individual reward 统计。
  - 对应模型名：`TD3_velodyne_multi_v4_coop`

- `动态RewardWeighted08/`
  - 动态 reward 的加权优化版。
  - 训练阶段使用 `0.8 * 自身 reward + 0.2 * 可见邻居 reward 均值`。
  - 额外保存 `best` checkpoint，避免高峰模型被 latest 覆盖。
  - 对应模型名：`TD3_velodyne_multi_v4_coop_weighted08`

- `局部邻域Critic/`
  - critic-only 消融实验。
  - 参考 MADDPG/CTDE 思想，让 critic 在训练时看到局部可见邻居信息。
  - actor 保持单机 observation 输入；critic 输入扩展为自身信息和按距离排序的邻居 context。
  - 目标是在不改变执行阶段观测条件的前提下，提高训练阶段对多机交互的价值估计能力。
  - 已加入环境容量验证流程，用于正式训练前检查 2、3、5、10 车是否可稳定运行。

## 正式产物位置

普通多智能体 baseline：

- `TD3/pytorch_models/TD3_velodyne_multi_v4_actor.pth`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_critic.pth`
- `TD3/checkpoints/TD3_velodyne_multi_v4_latest.pt`
- `TD3/results/TD3_velodyne_multi_v4.npy`
- `TD3/results/TD3_velodyne_multi_test.npy`
- `TD3/results/TD3_velodyne_multi_v4_baseline_fair300_test.npy`

动态 reward：

- `TD3/pytorch_models/TD3_velodyne_multi_v4_coop_actor.pth`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_coop_critic.pth`
- `TD3/checkpoints/TD3_velodyne_multi_v4_coop_latest.pt`
- `TD3/results/TD3_velodyne_multi_v4_coop.npy`
- `TD3/results/TD3_velodyne_multi_v4_coop_test.npy`

动态 reward 加权版：

- `TD3/pytorch_models/TD3_velodyne_multi_v4_coop_weighted08_actor.pth`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_coop_weighted08_critic.pth`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_coop_weighted08_best_actor.pth`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_coop_weighted08_best_critic.pth`
- `TD3/checkpoints/TD3_velodyne_multi_v4_coop_weighted08_latest.pt`
- `TD3/checkpoints/TD3_velodyne_multi_v4_coop_weighted08_best.pt`
- `TD3/results/TD3_velodyne_multi_v4_coop_weighted08.npy`
- `TD3/results/TD3_velodyne_multi_v4_coop_weighted08_best_test.npy`

局部邻域 critic 预期产物命名：

- `TD3/pytorch_models/TD3_velodyne_multi_v4_local_critic_actor.pth`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_local_critic_critic.pth`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_local_critic_best_actor.pth`
- `TD3/pytorch_models/TD3_velodyne_multi_v4_local_critic_best_critic.pth`
- `TD3/checkpoints/TD3_velodyne_multi_v4_local_critic_latest.pt`
- `TD3/checkpoints/TD3_velodyne_multi_v4_local_critic_best.pt`
- `TD3/results/TD3_velodyne_multi_v4_local_critic.npy`
- `TD3/results/TD3_velodyne_multi_v4_local_critic_best_test.npy`
