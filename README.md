# DRL-robot-navigation

本仓库基于开源项目 `reiniscimurs/DRL-robot-navigation` 做复现和进一步修改。工作重点不是从零重写导航系统，而是在原始 TD3 + ROS Gazebo 导航框架上，完成单智能体复现、扩展到同环境双机器人共享 policy，并继续探索局部动态 reward 对多机协同能力的影响。

## 项目定位

这里保留了原项目的基础环境、训练框架和论文背景，同时加入了当前这轮实验中的研究性改动：

- 完成单智能体训练与测试复现，得到可用 baseline。
- 扩展到同一个 Gazebo 环境下两个机器人共享同一个 TD3 policy 共同训练。
- 实现基于雷达可见邻居的动态 reward。
- 对比了动态 reward 完全平均与加权版本 `0.8 * self + 0.2 * neighbor_mean`。
- 增加 detached 训练/测试脚本、断点续跑、best checkpoint 保存和更清晰的控制台信息。
- 整理了实验归档、横向对比和正式日志，方便后续汇报与继续优化。

## 当前实验主线

目前正式保留 4 组实验：

1. `单智能体`
2. `多智能体/共享PolicyBaseline`
3. `多智能体/动态Reward`
4. `多智能体/动态RewardWeighted08`

其中当前效果最好的多智能体版本是 `动态RewardWeighted08`：

- `Success Rate = 0.889`
- `Collision Rate = 0.089`
- `Full Success Rate = 0.797`
- `Timeout Rate = 0.054`

完整横向对比见 [experiments/实验总览.md](experiments/实验总览.md)。

## 建议阅读顺序

如果第一次看这个仓库，建议按下面顺序：

1. [experiments/实验总览.md](experiments/实验总览.md)：看整体实验链条与结论。
2. [experiments/多智能体/README.md](experiments/多智能体/README.md)：看多智能体三版实验和产物位置。
3. [README_执行文档.md](README_执行文档.md)：看当前机器上的实际执行流程。

## 快速入口

### 单智能体

- 后台训练：`bash scripts/start_training_detached.sh`
- 后台测试：`bash scripts/start_test_detached.sh`

### 多智能体共享 Policy Baseline

- 后台训练：`bash scripts/start_training_detached_multi.sh`
- 公平 300 episode 测试：`bash scripts/start_test_detached_multi_baseline_fair300.sh`

### 多智能体动态 Reward

- 后台训练：`bash scripts/start_training_detached_multi_coop.sh`
- 后台测试：`bash scripts/start_test_detached_multi_coop.sh`

### 多智能体动态 Reward Weighted08

- 后台训练：`bash scripts/start_training_detached_multi_coop_weighted08.sh`
- 测试 best 模型：`bash scripts/start_test_detached_multi_coop_weighted08_best.sh`

更完整的执行说明见 [README_执行文档.md](README_执行文档.md)。

## 实验记录与日志

- 运行时日志默认写到 `logs/`，方便训练和测试过程中实时查看。
- 正式归档日志、实验总结和横向对比统一保存在 `experiments/`。
- 上传和汇报时，建议以 `experiments/` 下的正式归档为准。

## 仓库结构

```text
DRL-robot-navigation/
├── TD3/                      # 训练、测试、模型、checkpoint、结果
├── catkin_ws/                # ROS 工作区
├── scripts/                  # 单智能体/多智能体 detached 启停脚本
├── experiments/              # 实验归档、总结、正式 train/test 日志
├── README.md                 # 项目首页
└── README_执行文档.md         # 当前机器上的执行手册
```

## 当前修改重点

核心代码修改主要集中在以下文件：

- `TD3/train_velodyne_td3_multi.py`
  - 支持多智能体动态 reward 配置。
  - 支持 detached 训练中断后续跑。
  - 支持 `best` checkpoint 保存。
  - 增加更详细的训练状态输出。

- `TD3/test_velodyne_td3_multi.py`
  - 支持按环境变量切换测试模型和结果文件。
  - 支持目标 episode 数自动停止。

- `TD3/multi_agent_velodyne_env.py`
  - 加入邻域动态 reward 和加权动态 reward。
  - 记录每步的原始 reward、调整后 reward 和可见邻居信息。

## 上游项目与论文

本仓库基于以下开源项目和论文开展复现与改进：

- Original repository: `https://github.com/reiniscimurs/DRL-robot-navigation`
- Paper: `Goal-Driven Autonomous Exploration Through Deep Reinforcement Learning`

原始论文引用信息保留如下：

```bibtex
@ARTICLE{9645287,
  author={Cimurs, Reinis and Suh, Il Hong and Lee, Jin Han},
  journal={IEEE Robotics and Automation Letters},
  title={Goal-Driven Autonomous Exploration Through Deep Reinforcement Learning},
  year={2022},
  volume={7},
  number={2},
  pages={730-737},
  doi={10.1109/LRA.2021.3133591}
}
```

## 环境示意

训练示意：

![Training Example](training.gif)

Gazebo 环境：

![Gazebo Environment](env1.png)

Rviz：

![Rviz](velodyne.png)
