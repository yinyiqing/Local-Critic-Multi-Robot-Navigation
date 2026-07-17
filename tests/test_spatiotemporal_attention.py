import pathlib
import sys
import unittest

import numpy as np
import torch


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "TD3"))

from spatiotemporal_attention import (
    BaseActor,
    SpatioTemporalTD3,
    StagedAttentionActor,
)


class FixedReplay:
    def __init__(self):
        rng = np.random.default_rng(0)
        self.histories = rng.normal(size=(4, 6, 24)).astype(np.float32)
        self.actions = rng.uniform(-1.0, 1.0, size=(4, 2)).astype(np.float32)
        self.rewards = rng.normal(size=(4, 1)).astype(np.float32)
        self.dones = np.zeros((4, 1), dtype=np.float32)
        self.next_histories = rng.normal(size=(4, 6, 24)).astype(np.float32)
        self.groups = np.asarray(["standard", "dense", "standard", "dense"])

    def sample(self, batch_size):
        if batch_size != 4:
            raise ValueError("FixedReplay expects batch_size=4")
        return (
            self.histories,
            self.actions,
            self.rewards,
            self.dones,
            self.next_histories,
            self.groups,
        )


class StagedAttentionActorTest(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(0)
        self.base_actor = BaseActor()
        self.actor = StagedAttentionActor(
            self.base_actor,
            history_len=6,
            model_dim=16,
            num_heads=4,
        )
        self.history = torch.randn(4, 6, 24)

    def test_zero_initialized_attention_preserves_base_action(self):
        base_only = self.actor(self.history, attention_enabled=False)
        with_attention = self.actor(self.history, attention_enabled=True)
        torch.testing.assert_close(with_attention, base_only)

    def test_base_stage_does_not_backpropagate_through_attention(self):
        self.actor.zero_grad(set_to_none=True)
        self.actor(self.history, attention_enabled=False).sum().backward()

        self.assertTrue(
            any(parameter.grad is not None for parameter in self.base_actor.parameters())
        )
        self.assertTrue(
            all(parameter.grad is None for parameter in self.actor.encoder.parameters())
        )
        self.assertTrue(
            all(
                parameter.grad is None
                for parameter in self.actor.attention_head.parameters()
            )
        )

    def test_gate_targets_map_standard_and_dense(self):
        groups = np.asarray(["standard", "dense", "dense", "standard"])
        targets = SpatioTemporalTD3._gate_targets(groups, torch.device("cpu"))
        torch.testing.assert_close(
            targets,
            torch.tensor([[0.0], [1.0], [1.0], [0.0]]),
        )

        with self.assertRaises(ValueError):
            SpatioTemporalTD3._gate_targets(
                np.asarray(["standard", "pair"]), torch.device("cpu")
            )

    def test_optimizer_updates_only_the_active_stage(self):
        agent = SpatioTemporalTD3(
            BaseActor().state_dict(),
            history_len=6,
            model_dim=16,
            num_heads=4,
            base_actor_lr=1e-3,
            attention_lr=1e-3,
            critic_hidden_dim=16,
            device=torch.device("cpu"),
        )
        replay = FixedReplay()
        base_before = agent.actor.base_actor.layer_3.weight.detach().clone()
        attention_before = agent.actor.gate_head.bias.detach().clone()

        agent.train_step(
            replay,
            batch_size=4,
            policy_delay=1,
            actor_start_step=0,
            attention_start_step=10,
            actor_lr_warmup_steps=0,
            environment_step=5,
        )
        self.assertFalse(
            torch.equal(base_before, agent.actor.base_actor.layer_3.weight)
        )
        torch.testing.assert_close(attention_before, agent.actor.gate_head.bias)

        agent.train_step(
            replay,
            batch_size=4,
            policy_delay=1,
            actor_start_step=0,
            attention_start_step=10,
            actor_lr_warmup_steps=0,
            environment_step=20,
        )
        self.assertFalse(
            torch.equal(attention_before, agent.actor.gate_head.bias)
        )


if __name__ == "__main__":
    unittest.main()
