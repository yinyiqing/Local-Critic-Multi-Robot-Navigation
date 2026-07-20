import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "TD3"))

from hard_case_sampling import (
    apply_group_balanced_hard_case_weights,
    episode_failure_signal,
    update_failure_score,
)


class HardCaseSamplingTest(unittest.TestCase):
    def test_failure_signal_prioritizes_collisions_and_incomplete_episodes(self):
        success = episode_failure_signal(1, 0.0, 0.0)
        failed = episode_failure_signal(0, 0.4, 0.0)
        self.assertEqual(success, 0.0)
        self.assertGreater(failed, success)

    def test_weights_keep_groups_balanced_and_raise_hard_cases(self):
        cases = [
            {"scenario_id": "standard-easy", "group": "standard"},
            {"scenario_id": "standard-hard", "group": "standard"},
            {"scenario_id": "dense-easy", "group": "dense"},
            {"scenario_id": "dense-hard", "group": "dense"},
        ]
        scores = {
            "standard-hard": update_failure_score(0.0, 2.0, ema=0.0),
            "dense-hard": update_failure_score(0.0, 2.0, ema=0.0),
        }
        apply_group_balanced_hard_case_weights(cases, scores)

        by_id = {case["scenario_id"]: case["weight"] for case in cases}
        self.assertGreater(by_id["standard-hard"], by_id["standard-easy"])
        self.assertGreater(by_id["dense-hard"], by_id["dense-easy"])
        self.assertAlmostEqual(
            by_id["standard-easy"] + by_id["standard-hard"], 1.0
        )
        self.assertAlmostEqual(by_id["dense-easy"] + by_id["dense-hard"], 1.0)


if __name__ == "__main__":
    unittest.main()
