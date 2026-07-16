# 五车 Individual Active Probe Best 300 Episodes Test Summary

## Run

- model: `TD3_velodyne_multi_v4_individual_active_probe_5_best`
- source training: `train_multi_individual_active_probe_5_detached_20260601_091906.log`
- raw test log: `test_multi_individual_active_probe_5_best_detached_20260601_145111.raw.log.gz`
- clean log: `test_multi_individual_active_probe_5_best_300episodes_clean.log`
- episodes: 300
- agents: 5
- scenario: `standard`
- seed: 0

## Final Metrics

| metric | value |
| --- | ---: |
| success_rate | 0.869 |
| collision_rate | 0.087 |
| unresolved_rate | 0.045 |
| full_success_rate | 0.537 |
| timeout_episode_rate | 0.197 |
| avg_reward | 101.625 |
| avg_env_steps | 79.517 |
| avg_agent_samples | 137.693 |
| avg_final_distance | 0.414 |

## Counts

| item | count |
| --- | ---: |
| agent successes | 1304 / 1500 |
| agent collisions | 131 / 1500 |
| unresolved agents | 67 / 1500 |
| full-success episodes | 161 / 300 |
| timeout episodes | 59 / 300 |

## Histograms

- success_hist 0..5: `[0, 1, 8, 38, 92, 161]`
- collision_hist 0..5: `[201, 72, 22, 5, 0, 0]`

## Timeout Structure

| timeout subset | value |
| --- | ---: |
| timeout episodes | 59 |
| timeout success_hist 0..5 | `[0, 1, 4, 19, 35, 0]` |
| timeout collision_hist 0..5 | `[41, 14, 4, 0, 0, 0]` |
| timeout unresolved_hist 0..5 | `[0, 52, 6, 1, 0, 0]` |
| timeout avg_reward | 64.922 |
| timeout avg_agent_samples | 393.169 |
| timeout avg_final_distance | 0.717 |
| non-timeout avg_env_steps | 25.539 |
| non-timeout avg_agent_samples | 75.149 |
| non-timeout avg_final_distance | 0.340 |

## Interpretation

Individual Active Probe uses pure individual reward while preserving active-neighbor diagnostics. Its 300-episode result (`full_success_rate=0.537`) is close to baseline/H (`0.540`) and slightly below InteractionOnly Active (`0.553`). This weakens the claim that I's small improvement is caused by the local interaction penalty itself; short training, best-checkpoint selection, and run variance remain plausible explanations.

The timeout structure is more informative than the aggregate score. Most timeouts are not full-scene failures: 35/59 timeout episodes already have 4 successful agents, 19/59 have 3 successful agents, and 52/59 have only one unresolved agent. This supports the current deadlock diagnosis: many five-agent failures are long-tail last-agent or last-two-agent stalls after other agents have already completed and stopped in the physical scene.
