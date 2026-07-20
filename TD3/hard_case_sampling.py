"""Failure-aware sampling that preserves standard/dense group balance."""


def episode_failure_signal(full_success, collision_rate, timeout):
    return float(
        max(0.0, 1.0 - float(full_success))
        + max(0.0, float(collision_rate))
        + max(0.0, float(timeout))
    )


def update_failure_score(previous, signal, ema=0.9):
    if not 0.0 <= ema < 1.0:
        raise ValueError("EMA must be in [0, 1)")
    return float(ema * float(previous) + (1.0 - ema) * max(float(signal), 0.0))


def apply_group_balanced_hard_case_weights(
    cases, scores, strength=1.5, uniform_fraction=0.3
):
    """Update manifest weights while keeping total standard/dense weight at 1:1."""
    if strength < 0.0 or not 0.0 <= uniform_fraction <= 1.0:
        raise ValueError("Invalid hard-case sampling parameters")

    groups = {}
    for case in cases:
        groups.setdefault(case["group"], []).append(case)
    for group_cases in groups.values():
        count = len(group_cases)
        raw = [
            1.0 + strength * max(float(scores.get(case["scenario_id"], 0.0)), 0.0)
            for case in group_cases
        ]
        raw_total = sum(raw)
        for case, value in zip(group_cases, raw):
            uniform_weight = uniform_fraction / count
            failure_weight = (1.0 - uniform_fraction) * value / raw_total
            case["weight"] = uniform_weight + failure_weight
