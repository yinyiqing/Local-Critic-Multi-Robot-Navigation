# 集中式 Critic 核查

## 这条线在做什么

- 不先乱调 actor
- 先确认 critic 这条线有没有改对
- 看 critic 看到更完整的多车信息后，actor 解冻会不会更稳

## 已完成的短对照

| 实验 | success_rate | collision_rate | full_success_rate |
| --- | --- | --- | --- |
| 新版 critic | 0.917 | 0.083 | 0.625 |
| 旧版 critic | 0.833 | 0.167 | 0.417 |

- critic 输入改法是有影响的
- 不是所有 actor 一解冻都会立刻崩

## 已完成的代码核查

- 查过：
  - buffer 里有没有多车信息
  - critic 训练时到底看到了什么
  - 更新当前车时，其他车是不是只当背景
  - target 和 mask 有没有明显问题
- 其他车不会跟着当前车一起乱更新
- 这块不是主要 bug
- 但 target 动作构造原来不够标准

## 已做的小修正

- 已把 target 动作的噪声处理补标准：
  - 不再只给当前车加
  - 而是所有车统一处理

## 当前下一步

- 正在跑一组中程验证：
  - 同场景
  - 同 warm start
  - 用修正后的新版 critic
  - 跑 `5 epoch`
- 目的：
  - 看短期优势能不能在更长训练里保持

## 目录说明

- [有效日志](/home/jiutian/Local-Critic-Multi-Robot-Navigation/experiments/多智能体/课程学习/后续计划_集中式Critic核查/有效日志)
  - 已完成的有效短对照日志
- [废弃日志](/home/jiutian/Local-Critic-Multi-Robot-Navigation/experiments/多智能体/课程学习/后续计划_集中式Critic核查/废弃日志)
  - 启动失败、中断、无效日志
- 这个目录只保留：
  - 一个总 README
  - 一个有效日志文件夹
  - 一个废弃日志文件夹

## 一句话总结

- 先发现旧版 critic 看到的多车信息不够完整
- 再把多车信息补进训练数据和 critic 输入里
- 然后继续看 critic 改对以后，actor 解冻还会不会像以前那样明显退化
