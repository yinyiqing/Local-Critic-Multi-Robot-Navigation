# 五车 InteractionOnly Active Best 300 Episodes Test Summary

## Run

- model: `TD3_velodyne_multi_v4_interaction_only_active_5_best`
- source training: `train_multi_interaction_only_active_5_detached_20260531_144304.log`
- test log: `test_multi_interaction_only_active_5_best_detached_20260531_215232.raw.log`
- episodes: 300
- agents: 5
- scenario: `standard`
- seed: 0

## Final Metrics

| metric | value |
| --- | ---: |
| success_rate | 0.881 |
| collision_rate | 0.069 |
| unresolved_rate | 0.051 |
| full_success_rate | 0.553 |
| timeout_episode_rate | 0.230 |
| avg_reward | 105.560 |
| avg_env_steps | 95.197 |
| avg_agent_samples | 164.460 |
| avg_final_distance | 0.392 |

## Counts

| item | count |
| --- | ---: |
| agent successes | 1321 / 1500 |
| agent collisions | 104 / 1500 |
| unresolved agents | 77 / 1500 |
| full-success episodes | 166 / 300 |
| timeout episodes | 69 / 300 |

## Histograms

- success_hist 0..5: `[0, 1, 1, 40, 92, 166]`
- collision_hist 0..5: `[213, 71, 15, 1, 0, 0]`

## Interpretation

InteractionOnly Active is the current best 300-episode result by full-success rate, but the margin is small: `0.553` versus baseline/H at `0.540`. It also keeps collision rate low (`0.069`), close to H (`0.071`) and below baseline (`0.107`).

The main remaining weakness is long-tail completion: `timeout_episode_rate=0.230` and `avg_env_steps=95.197`, nearly the same timeout level as H. So this result supports replacing full neighbor reward averaging with local interaction shaping, but it does not fully solve five-agent timeout/deadlock behavior.
