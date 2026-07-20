import pathlib
import sys
import unittest

import numpy as np


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "TD3"))

from interaction_risk import interaction_risk


class InteractionRiskTest(unittest.TestCase):
    def test_risk_is_zero_without_visible_neighbors(self):
        risk = interaction_risk(
            [0.0, 0.0],
            [0.0, 0.0],
            0.0,
            np.empty((0, 2)),
            np.empty((0, 2)),
        )
        self.assertEqual(risk, 0.0)

    def test_close_approaching_robot_has_high_risk(self):
        risk = interaction_risk(
            [0.0, 0.0],
            [0.5, 0.0],
            0.0,
            [[0.5, 0.0]],
            [[-0.5, 0.0]],
        )
        self.assertGreater(risk, 0.6)

    def test_robot_outside_field_of_view_is_not_labeled(self):
        risk = interaction_risk(
            [0.0, 0.0],
            [0.0, 0.0],
            0.0,
            [[-0.5, 0.0]],
            [[0.0, 0.0]],
        )
        self.assertEqual(risk, 0.0)


if __name__ == "__main__":
    unittest.main()
