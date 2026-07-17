# Fixed Standard/Dense Scenarios v1 - Migration Bundle

这个目录用于把冻结的 `standard` 和 `dense` 五车场景迁移到另一个项目。数据在任何正式 Actor/gate 实验前完成冻结，并通过策略无关的 Gazebo reset 检查。

## 包含内容

```text
data/fixed_v1/                 13,500 个正式 train/validation/test manifest
runtime/TD3/                   生成、读取和检查 manifest 的 Python 模块
runtime/scripts/               生成、Gazebo 筛选、审计和 launch 生成工具
runtime/tests/                 不依赖 Gazebo 的单元测试
simulator/multi_robot_scenario 完整 ROS 场景包、TD3.world、P3DX 模型和传感器配置
launch/                        现成的五车 headless launch
integration/                   同源项目的 manifest 接入补丁
```

不包含：Actor 权重、训练 checkpoint、结果、日志、pilot 和可重建的候选全集。

## 数据规模

| Pool | train | validation | test |
| --- | ---: | ---: | ---: |
| standard | 3000 | 500 | 1000 |
| dense | 6000 | 1000 | 2000 |

Gate 不需要第三个场景池，直接混合两个 train split。

## 必须保持的兼容条件

这些坐标不是与地图无关的通用数据。正式复现实验必须保持：

- `TD3.world` 的静态墙体与障碍几何。
- Pioneer3DX 的碰撞尺寸、Velodyne 配置和五个模型名 `r1-r5`。
- 四个动态箱子模型名 `cardboard_box_0-3`。
- 到达阈值 `0.3 m`、碰撞阈值 `0.35 m` 和相同动作步进逻辑。
- reset 时完整恢复 start、goal、heading 和 boxes，不能再次随机或添加 jitter。

如果另一个项目使用不同地图或机器人尺寸，这批数据只能作为坐标样例，不能继续声称是同一个 benchmark，必须重新做 Gazebo 有效性筛选。

## 同源项目接入

假设目标项目目录结构与本项目相同：

1. 将 `simulator/multi_robot_scenario/` 放入目标项目 `catkin_ws/src/`。
2. 将 `runtime/TD3/*.py` 放入目标项目 `TD3/`。
3. 将需要的 `runtime/scripts/*.py` 放入目标项目 `scripts/`。
4. 将 `data/fixed_v1/` 放到目标项目的数据目录。
5. 对接近提交 `975871d` 的同源代码，先在目标项目运行：

```bash
git apply --check /path/to/fixed_scenarios_v1/integration/manifest_support.patch
git apply /path/to/fixed_scenarios_v1/integration/manifest_support.patch
```

补丁只负责把 manifest 模式接入多机器人环境和 train/test 日志。目标代码如果已经发生较大变化，不要强行应用；按照下一节的回放契约手动接入。

## 异构项目回放契约

环境需要支持 `manifest` scenario mode：

1. 启动时读取一个 `.json` 或 `.json.gz` split。
2. 检查 manifest agent 名称与环境模型严格一致。
3. 每次 reset 选择一条 scenario。
4. 将 `agents.rN.start`、`goal`、`heading` 和 `boxes` 原样写入仿真。
5. 训练使用随机抽样；验证和测试使用文件顺序循环。
6. 日志必须记录 `scenario_id`，以便不同 Actor 做逐场 paired comparison。

本项目约定的环境变量：

```bash
export DRL_MULTI_SCENARIO=manifest
export DRL_MULTI_MANIFEST_PATH=/path/to/fixed_v1/dense/test.json.gz
export DRL_MULTI_MANIFEST_SAMPLING=cycle  # train 使用 random
```

## 验证迁移

先做纯数据审计：

```bash
python runtime/scripts/audit_fixed_scenarios.py \
  data/fixed_v1/{standard,dense}/{train,validation,test}.json.gz

python -m unittest discover -s runtime/tests -v
```

然后至少抽取少量场景重新运行 Gazebo reset 检查。不要用 Actor 成功率决定删除哪些 test 场景。

正式数据的 SHA-256、唯一拒绝场景和生成 seed 见 [data/fixed_v1/README.md](data/fixed_v1/README.md)。

## 来源

- 数据冻结提交：`97fed70`
- manifest 管线提交：`9a3de1e`
- 原始工作区：`Local-Critic-Multi-Robot-Navigation-gate`
