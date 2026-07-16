# Local-Critic-Multi-Robot-Navigation

本仓库基于 `reiniscimurs/DRL-robot-navigation` 的单智能体 TD3 局部导航实现，目标是把它扩展为同一环境内的多智能体局部导航系统。

## 实验主线

原始项目解决的是单个机器人到达单个目标的问题。本项目要解决的问题是：

**多个机器人同时处于同一个 ROS/Gazebo 环境中，每个机器人都有自己的起点和目标点；机器人需要在相互影响、相互避碰的同时，分别完成自己的导航任务。**

主线演进关系为：

```text
单智能体 TD3 局部导航
  -> 同一环境内的多机器人训练与测试
  -> 多车交互场景和统一评价体系
  -> 使用 Attention 学习多车交互的空间与时间信息
  -> 提高每台车到达目标以及全体同时完成任务的能力
```

多机器人任务不是把若干个互不相关的单车任务并排运行。其他机器人会持续改变本车可行的速度和转向选择，因此策略必须学习避让、通过次序和动态冲突消解。

## 任务定义

- 同一场景中同时运行多台机器人。
- 每台机器人拥有独立的起点、目标点、动作和结束状态。
- 所有机器人需要避开静态障碍物以及其他正在运动的机器人。
- 每台机器人独立到达自己的目标才算个体成功；所有机器人都成功才算整局完全成功。
- 当前采用共享策略、分散执行：每台机器人使用同一个 Actor，但只根据本车观测选择动作。

每帧本车观测为 24 维：

```text
20 维激光距离 + 目标距离/方向 + 上一步动作
```

执行阶段不直接读取其他机器人的 Gazebo 真值位置、目标或动作。其他车辆的存在和运动主要通过本车连续激光观测体现。

## 核心方法

TD3 仍作为连续动作强化学习的基础算法，Attention 是当前主要新增模块，用于从本车观测序列中提取多车交互的时空信息：

- 空间 Attention：处理同一时刻的激光扇区，关注可能发生冲突的方向和邻近车辆。
- 时间 Attention：处理连续多帧观测，识别其他车辆的接近、远离和横向穿越趋势。
- 时空特征参与动作决策，使机器人不只对当前最近距离做瞬时反应，还能根据交互变化调整速度和转向。

当前代码采用一条保守的实现路径：冻结已有的 `5D` 多车 Actor，让 Attention 根据最近 6 帧本车观测输出有界残差动作。这个结构是当前实验实现，不是研究目标本身；研究目标始终是验证 Attention 能否提高多机器人交互导航能力。

核心实验假设是：**在相同 TD3 基础、观测边界、训练场景和评价条件下，时空 Attention 应当比无 Attention 的策略更好地处理多车交互。**

## 评价目标

实验至少同时报告以下指标：

- `success_rate`：所有机器人中的个体到达率。
- `collision_rate`：所有机器人中的个体碰撞率。
- `full_success_rate`：整局中所有机器人都到达各自目标的比例。
- `timeout_rate`：未在规定步数内完成任务的比例。

`full_success_rate` 是多机器人任务的核心指标。只提高部分机器人的成功率、但让其他机器人持续碰撞或超时，不算完成多智能体导航目标。

## 当前实现

旧课程、局部 Critic、奖励塑形和双 Actor 等实验已经移入 `trash/MRNA_refactor_20260716/`。当前工作区只保留单车、多车共享策略、冻结 `5D` 和当前 Attention 所需的代码、入口与模型。

当前实现为：

```text
冻结 5D 多车 Actor
  + 最近 6 帧本车观测
  + 激光扇区空间 Attention
  + 时间 Attention
  + 门控残差动作
```

后续所有结构调整和实验对照都应围绕同一个问题展开：**Attention 是否真正学到了有助于多车交互的时空信息，并因此提高多机器人各自到达目标的能力。**

## 对照 Baseline

| Baseline | 用途 | 入口 | 模型前缀 |
| --- | --- | --- | --- |
| 单智能体 TD3 | 验证原始局部导航与基础训练链路 | `start_training_detached.sh` | `TD3_velodyne` |
| 通用多智能体 TD3 | 验证共享策略和同场多车流程 | `start_training_detached_multi.sh` | `TD3_velodyne_multi_v4` |
| 五车共享策略 | 无 Attention 的直接五车对照 | `start_training_detached_multi_baseline_5.sh` | `TD3_velodyne_multi_v4_shared_policy_5_best` |
| 冻结 `5D` | 当前 Attention 的基础 Actor 和强多车对照 | `start_test_detached_multi_5d_baseline.sh` | `TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best` |

保留 `5D` 只是因为当前 Attention 初始化和消融直接依赖该模型，不表示继续沿用旧课程研究。新实验必须与适用的 baseline 在相同场景、随机种子、回合数和指标口径下比较，不能只和旧 Attention 版本纵向比较。

## 文档入口

1. [Attention 方法与消融](experiments/attention/README.md)

## 运行指南

### 环境

推荐使用仓库提供的 ROS Noetic Docker 环境：宿主机需要 NVIDIA GPU 和 Docker NVIDIA runtime；容器提供 Ubuntu 20.04、ROS Noetic、Gazebo 和独立 Python 环境。

构建镜像：

```bash
bash scripts/docker_build_noetic.sh
```

### Attention 训练

宿主机已安装 ROS Noetic 和项目虚拟环境时：

```bash
bash scripts/start_training_detached_spatiotemporal_attention_5d.sh
bash scripts/stop_training_detached_spatiotemporal_attention_5d.sh
```

使用 Docker：

```bash
DRL_DOCKER_TRAIN_MODE=attention5d bash scripts/docker_train_noetic.sh
bash scripts/docker_stop_noetic.sh
```

模型结构、场景分组和消融要求见 [Attention 方法文档](experiments/attention/README.md)。训练日志默认写入 `logs/attention/`。

### Baseline

```bash
# 单智能体 TD3
bash scripts/start_training_detached.sh
bash scripts/start_test_detached.sh

# 通用多智能体 TD3
bash scripts/start_training_detached_multi.sh
bash scripts/start_test_detached_multi.sh

# 五车共享策略
bash scripts/start_training_detached_multi_baseline_5.sh
bash scripts/start_test_detached_multi_baseline_5_best.sh

# 冻结 5D
bash scripts/start_test_detached_multi_5d_baseline.sh
```

### 监控

后台脚本会在终端打印 PID 和日志路径。查看训练日志：

```bash
tail -f logs/attention/<log-file>.log
```

启动 TensorBoard：

```bash
source env.python.sh
tensorboard --logdir TD3/runs --bind_all --port 6006
```

### 基础设施

```bash
# 编译 catkin 工作区
bash scripts/build_readme_workspace.sh

# 生成五车 launch
python3 scripts/generate_multi_robot_launch.py \
  --num-agents 5 \
  --output TD3/assets/multi_robot_scenario_multi_5.launch

# 容量检查
bash scripts/start_capacity_check_multi.sh 5
bash scripts/stop_capacity_check_multi.sh 5
```

## 仓库结构

```text
Local-Critic-Multi-Robot-Navigation/
├── TD3/               # 环境、模型、训练和测试代码
├── catkin_ws/         # ROS 工作区、机器人模型和 Gazebo 插件
├── scripts/           # 训练、测试、停止和观察脚本
├── experiments/       # 当前 Attention 方法和场景定义
└── trash/             # 已退出主线的可恢复归档
```
