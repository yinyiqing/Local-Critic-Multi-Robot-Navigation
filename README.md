# Local-Critic-Multi-Robot-Navigation

本仓库基于开源项目 `reiniscimurs/DRL-robot-navigation` 做复现和多机器人导航研究。当前工作重点是：在 TD3 + ROS/Gazebo 导航框架上，研究共享 policy、动态 reward 和局部邻域 critic 对多机器人协同导航的影响。

## 项目定位

本项目不是从零重写导航系统，而是在原始单机器人 TD3 导航框架上逐步扩展：

- 单智能体 TD3 导航复现。
- 多机器人共享 actor/critic policy。
- RewardOnly 与 Weighted08 动态 reward 对照。
- 局部邻域 critic：actor 执行时仍只看自身观测，邻居几何信息只进入训练期 critic。

## 当前主线

当前主线是三车对照实验：

- warm-start：`TD3_velodyne_multi_v4`
- actor 输入：本车 24 维 observation
- 执行阶段：无通信，不使用邻居信息
- 测试规模：best actor 300 episodes

核心实验：

| 方法 | 简述 |
| --- | --- |
| A. 三车共享 Policy Baseline | 共享 actor/critic，不使用动态 reward 和局部 critic |
| B. 三车 RewardOnly | 只改变训练 reward |
| C. 三车 Weighted08 | `0.8 * own + 0.2 * distance-weighted neighbor` |
| D. 三车局部邻域 Critic | critic 看邻居几何和邻居动作 |
| D2. 三车几何邻域 Critic | critic 只看邻居几何信息 |

当前最有价值的结果是 D2：三车几何邻域 Critic 在 20 epoch 扩展验证中达到 `full_success_rate=0.827`，高于三车 baseline、RewardOnly、Weighted08 和原始局部邻域 Critic。

完整横向对比见：

- [experiments/实验总览.md](experiments/实验总览.md)
- [experiments/多智能体/三车主线对照总表.md](experiments/多智能体/三车主线对照总表.md)

## 建议阅读顺序

1. [experiments/实验总览.md](experiments/实验总览.md)
2. [experiments/多智能体/三车主线对照总表.md](experiments/多智能体/三车主线对照总表.md)
3. [experiments/多智能体/README.md](experiments/多智能体/README.md)

## 快速入口

### 三车共享 Policy Baseline

```bash
bash scripts/start_training_detached_multi_baseline_3.sh
bash scripts/start_test_detached_multi_baseline_3_best.sh
```

### 三车 RewardOnly

```bash
bash scripts/start_training_detached_multi_reward_only_3.sh
bash scripts/start_test_detached_multi_reward_only_3_best.sh
```

### 三车 Weighted08

```bash
bash scripts/start_training_detached_multi_weighted08_3.sh
bash scripts/start_test_detached_multi_weighted08_3_best.sh
```

### 三车局部邻域 Critic

```bash
bash scripts/start_training_detached_multi_local_critic_3.sh
bash scripts/start_test_detached_multi_local_critic_3_best.sh
```

### 三车几何邻域 Critic

```bash
bash scripts/start_training_detached_multi_local_critic_geo_3.sh
bash scripts/start_test_detached_multi_local_critic_geo_3_best.sh
```


## 实验记录与日志

- 正式归档放在 `experiments/`。
- 三车主线结果以各实验目录中的 `*_summary.md` 为准。

## 仓库结构

```text
Local-Critic-Multi-Robot-Navigation/
├── TD3/                      # 训练、测试、模型、checkpoint、结果
├── catkin_ws/                # ROS 工作区
├── scripts/                  # detached 启停脚本
├── experiments/              # 实验归档、总结、正式 train/test 日志
├── README.md                 # 项目首页
└── README_执行文档.md         # 当前机器上的执行手册
```
