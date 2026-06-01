# 五车 DoneAgentRelocate Best 300 Episodes Test Summary

## Run

- model: `TD3_velodyne_multi_v4_individual_active_probe_5_best`
- source training: `train_multi_individual_active_probe_5_detached_20260601_091906.log`
- base checkpoint: J group epoch 3 best
- raw test log: `test_multi_individual_active_probe_5_best_relocate_done_detached_20260601_164040.raw.log.gz`
- clean log: `test_multi_individual_active_probe_5_best_relocate_done_300episodes_clean.log`
- episodes: 300
- agents: 5
- scenario: `standard`
- seed: 0
- test-only intervention: successful done agents relocated to holding area

## Final Metrics

| metric | value |
| --- | ---: |
| success_rate | 0.869 |
| collision_rate | 0.095 |
| unresolved_rate | 0.039 |
| full_success_rate | 0.533 |
| timeout_episode_rate | 0.167 |
| avg_reward | 101.268 |
| avg_env_steps | 71.007 |
| avg_agent_samples | 128.277 |
| avg_final_distance | 0.409 |

## Counts

| item | count |
| --- | ---: |
| agent successes | 1303 / 1500 |
| agent collisions | 142 / 1500 |
| unresolved agents | 58 / 1500 |
| full-success episodes | 160 / 300 |
| timeout episodes | 50 / 300 |

## Histograms

- success_hist 0..5: `[0, 2, 7, 37, 94, 160]`
- collision_hist 0..5: `[190, 82, 25, 2, 1, 0]`

## Timeout Structure

| timeout subset | value |
| --- | ---: |
| timeout episodes | 50 |
| timeout success_hist 0..5 | `[0, 1, 5, 17, 27, 0]` |
| timeout collision_hist 0..5 | `[32, 14, 4, 0, 0, 0]` |
| timeout unresolved_hist 0..5 | `[0, 42, 8, 0, 0, 0]` |
| timeout avg_reward | 61.683 |
| timeout avg_agent_samples | 404.540 |
| timeout avg_final_distance | 0.740 |
| non-timeout avg_env_steps | 25.208 |
| non-timeout avg_agent_samples | 73.024 |
| non-timeout avg_final_distance | 0.343 |

## Interpretation

Relocating successful done agents reduces timeout episodes from J's 59/300 to 50/300 and lowers `avg_env_steps` from 79.517 to 71.007. This confirms that stopped successful agents can contribute to long-tail completion time.

However, the main full-success metric does not improve: `full_success_rate=0.533` versus J's `0.537`. Collision rate also rises from `0.087` to `0.095`. Therefore, the static-success-agent hypothesis is only a partial explanation. It affects timeout efficiency, but it is not the dominant reason five-agent full-success remains low.
