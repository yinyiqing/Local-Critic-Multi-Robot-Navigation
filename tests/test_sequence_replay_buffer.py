import pathlib
import sys
import unittest

import numpy as np


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "TD3"))

from sequence_replay_buffer import SequenceReplayBuffer


def transition(value):
    history = np.full((6, 24), value, dtype=np.float32)
    return history, np.array([0.0, 0.0], dtype=np.float32), 0.0, 0.0, history


class SequenceReplayBufferTest(unittest.TestCase):
    def test_sample_returns_interaction_risk(self):
        buffer = SequenceReplayBuffer(8, seed=0)
        buffer.add(*transition(0.0), group="standard", interaction_risk=0.2)
        buffer.add(*transition(1.0), group="dense", interaction_risk=0.8)

        *_, groups, risks = buffer.sample(2)
        self.assertEqual(set(groups.tolist()), {"standard", "dense"})
        self.assertEqual(risks.shape, (2, 1))
        self.assertEqual({round(float(value), 1) for value in risks[:, 0]}, {0.2, 0.8})

    def test_loads_pre_risk_checkpoint_entries(self):
        source = SequenceReplayBuffer(8, seed=0)
        source.add(*transition(0.0), group="standard", interaction_risk=0.6)
        source.add(*transition(1.0), group="dense", interaction_risk=0.9)
        state = source.state_dict()
        state["version"] = 2
        state["buffer"] = [
            (group, stored_transition[:5])
            for group, stored_transition in state["buffer"]
        ]

        restored = SequenceReplayBuffer(8, seed=1)
        restored.load_state_dict(state)
        *_, risks = restored.sample(2)
        np.testing.assert_array_equal(risks, np.zeros((2, 1), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
