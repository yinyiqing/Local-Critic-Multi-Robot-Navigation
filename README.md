# Local-Critic-Multi-Robot-Navigation

本仓库基于 `reiniscimurs/DRL-robot-navigation`，研究 TD3 在 ROS/Gazebo 多机器人局部导航中的训练与泛化。机器人执行时只使用本车 24 维观测；训练阶段可以通过局部 Critic 使用邻居信息。

## 当前研究主线

历史实验收敛出的能力链路是：

```text
5A（普通五车 Actor）
  -> 5D（几何邻域 Critic 训练得到的桥接 Actor）
  -> PAIR(from_5d) / THREE_5（证明继续覆盖训练会退化）
  -> 5D + 时空 Attention 残差（当前主线）
```

现有结果支持以下判断：

- `5A` 是普通导航主干。
- `5D` 在当前正式 dense 测试中表现最好，是桥接基线。
- `PAIR(from_5d)` 的训练过程更顺，但正式 dense 测试没有超过 `5D`；继续训练到 `THREE_5` 后逐轮退化。
- `5A + 5D` 的 hard switch 和 case-level oracle 都没有超过单独使用 `5D`，二者暂时缺乏足够的专家互补性。

因此当前不再覆盖训练完整 Actor，也不再训练双 Actor gate。新主线冻结 `5D`，只训练使用本车观测历史的时空 Attention 残差；Critic 使用两个独立的轻量 full-history MLP Q 网络。

## 方法结构

Actor 在所有主要实验中保持分散执行：

```text
20 维激光 + 目标距离/方向 + 上一步动作
  -> 共享 Actor
  -> 线速度与角速度
```

主要 Critic 变体包括：

- 共享 Critic：只使用本车状态和动作。
- 局部 Critic：训练时加入邻居几何及可选动作信息。
- 几何邻域 Critic：只加入邻居几何，不依赖邻居动作。
- 时空 Attention：使用本车激光扇区和最近观测历史，输出对冻结 `5D` 的门控残差动作。
- Full-history MLP Critic：两个独立 Q 网络都读取本车最近 6 帧 24 维观测历史和当前动作，不使用其他机器人的仿真真值。

## 建议阅读顺序

1. [实验总览](experiments/实验总览.md)
2. [课程学习](experiments/02_课程学习/README.md)
3. [五车非对称密集重做](experiments/02_课程学习/第三课程_多车密集交互/05_五车非对称密集重做/README.md)
4. [保留专门化](experiments/04_保留专门化/README.md)
5. [时空 Attention 残差主线](experiments/04_保留专门化/03_门控注意力增强/README.md)
6. [双 Actor 切换与 Oracle（历史诊断）](experiments/04_保留专门化/02_双actor切换/README.md)
7. [执行文档](README_执行文档.md)

早期三车 A/B/C/D/D2 对照仍保留为历史实验，见 [第一次尝试](experiments/01_第一次尝试/多智能体/3智能体/三车主线对照总表.md)，不再作为当前主线入口。

## 当前执行入口

```bash
# 当前唯一的新训练主线
bash scripts/start_training_detached_spatiotemporal_attention_5d.sh

# 5D standard_5 正式测试
bash scripts/start_test_detached_multi_stage2_to_5d_geo_critic_from_5a_guarded_best.sh

```

具体环境变量、后台进程和 ROS/Gazebo 操作见 [README_执行文档.md](README_执行文档.md)。

## 仓库结构

```text
Local-Critic-Multi-Robot-Navigation/
├── TD3/              # 训练、测试、环境、模型与 checkpoint
├── catkin_ws/        # ROS 工作区、机器人模型和 Gazebo 插件
├── scripts/          # 训练、测试、停止与观察脚本
├── experiments/      # 实验设计、正式结果和结论
└── README_执行文档.md # 当前机器执行手册
```
