# 五车 Individual Anti-Stagnation Best 300 Episodes Test Summary

## Run

- model: `TD3_velodyne_multi_v4_individual_antistagnation_5_best`
- source training: `train_multi_individual_antistagnation_5_detached_20260601_194529.log`
- raw test log partial: `test_multi_individual_antistagnation_5_best_detached_20260601_233854.partial.raw.log.gz`
- raw test log resume: `test_multi_individual_antistagnation_5_best_detached_20260601_234131.resume.raw.log.gz`
- clean log: `test_multi_individual_antistagnation_5_best_300episodes_clean.log`
- episodes: 300
- agents: 5
- scenario: `standard`
- seed: 0

## Final Metrics

| metric | value |
| --- | ---: |
| success_rate | 0.864 |
| collision_rate | 0.125 |
| unresolved_rate | 0.015 |
| full_success_rate | 0.530 |
| timeout_episode_rate | 0.073 |
| avg_reward | 100.571 |
| avg_env_steps | 45.620 |
| avg_agent_samples | 96.807 |
| avg_final_distance | 0.404 |

## Counts

| item | count |
| --- | ---: |
| agent successes | 1296 / 1500 |
| agent collisions | 187 / 1500 |
| unresolved agents | 22 / 1500 |
| full-success episodes | 159 / 300 |
| timeout episodes | 22 / 300 |

## Timeout Structure

| timeout subset | value |
| --- | ---: |
| timeout episodes | 22 |
| timeout success_hist 0..5 | `[0, 1, 3, 8, 10, 0]` |

## Comparison To J

| method | success_rate | collision_rate | unresolved_rate | full_success_rate | timeout_episode_rate | avg_env_steps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| J Individual Active Probe | 0.869 | 0.087 | 0.045 | 0.537 | 0.197 | 79.517 |
| M Individual Anti-Stagnation | 0.864 | 0.125 | 0.015 | 0.530 | 0.073 | 45.620 |

## Interpretation

M reduces timeout episodes and unresolved agents relative to J, but it does not improve the main benchmark target. `full_success_rate` drops from J's `0.537` to `0.530`, and `collision_rate` rises from `0.087` to `0.125`.

This is a useful negative result. The anti-stagnation reward appears to reduce long tail waiting, but it does not fix the underlying local navigation failures. Based on RViz observation and L/M diagnostics, the remaining failures are better treated as near-goal capture and wall-separated-goal local-minimum problems, not as a reward averaging or local critic problem.
