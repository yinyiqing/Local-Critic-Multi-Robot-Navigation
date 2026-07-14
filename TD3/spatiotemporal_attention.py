import copy
import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class BaseActor(nn.Module):
    def __init__(self, state_dim=24, action_dim=2):
        super().__init__()
        self.layer_1 = nn.Linear(state_dim, 800)
        self.layer_2 = nn.Linear(800, 600)
        self.layer_3 = nn.Linear(600, action_dim)

    def forward(self, state):
        state = F.relu(self.layer_1(state))
        state = F.relu(self.layer_2(state))
        return torch.tanh(self.layer_3(state))


class SpatioTemporalEncoder(nn.Module):
    def __init__(
        self,
        history_len=6,
        laser_dim=20,
        robot_dim=4,
        model_dim=96,
        num_heads=4,
    ):
        super().__init__()
        if model_dim % num_heads != 0:
            raise ValueError("model_dim must be divisible by num_heads")
        self.history_len = int(history_len)
        self.laser_dim = int(laser_dim)
        self.robot_dim = int(robot_dim)

        half_bin = math.pi / (2.0 * self.laser_dim)
        angles = torch.linspace(
            -math.pi / 2.0 + half_bin,
            math.pi / 2.0 - half_bin,
            self.laser_dim,
        )
        self.register_buffer(
            "laser_geometry",
            torch.stack((torch.sin(angles), torch.cos(angles)), dim=-1),
            persistent=False,
        )
        self.laser_projection = nn.Linear(3, model_dim)
        self.robot_projection = nn.Linear(robot_dim, model_dim)
        self.spatial_attention = nn.MultiheadAttention(
            model_dim, num_heads, batch_first=True
        )
        self.spatial_norm = nn.LayerNorm(model_dim)

        self.temporal_position = nn.Parameter(
            torch.zeros(1, self.history_len, model_dim)
        )
        nn.init.normal_(self.temporal_position, std=0.02)
        self.temporal_attention = nn.MultiheadAttention(
            model_dim, num_heads, batch_first=True
        )
        self.temporal_norm = nn.LayerNorm(model_dim)
        self.feed_forward = nn.Sequential(
            nn.Linear(model_dim, model_dim * 2),
            nn.ReLU(),
            nn.Linear(model_dim * 2, model_dim),
        )
        self.output_norm = nn.LayerNorm(model_dim)

    def forward(self, history):
        if history.ndim != 3:
            raise ValueError("history must have shape [batch, time, state]")
        batch_size, time_steps, state_dim = history.shape
        expected_dim = self.laser_dim + self.robot_dim
        if time_steps != self.history_len or state_dim != expected_dim:
            raise ValueError(
                "expected history shape [batch, %d, %d], got %s"
                % (self.history_len, expected_dim, tuple(history.shape))
            )

        laser = history[:, :, : self.laser_dim]
        robot = history[:, :, self.laser_dim :]
        geometry = self.laser_geometry.view(1, 1, self.laser_dim, 2).expand(
            batch_size, time_steps, -1, -1
        )
        laser_tokens = torch.cat((laser.unsqueeze(-1), geometry), dim=-1)
        laser_tokens = self.laser_projection(laser_tokens).reshape(
            batch_size * time_steps, self.laser_dim, -1
        )
        robot_query = self.robot_projection(robot).reshape(
            batch_size * time_steps, 1, -1
        )
        spatial_context, _ = self.spatial_attention(
            robot_query, laser_tokens, laser_tokens, need_weights=False
        )
        frame_features = self.spatial_norm(robot_query + spatial_context).reshape(
            batch_size, time_steps, -1
        )

        temporal_input = frame_features + self.temporal_position
        temporal_context, _ = self.temporal_attention(
            temporal_input, temporal_input, temporal_input, need_weights=False
        )
        temporal_features = self.temporal_norm(temporal_input + temporal_context)
        temporal_features = self.output_norm(
            temporal_features + self.feed_forward(temporal_features)
        )
        return temporal_features[:, -1]


class ResidualAttentionActor(nn.Module):
    def __init__(
        self,
        base_actor,
        history_len=6,
        state_dim=24,
        action_dim=2,
        model_dim=96,
        num_heads=4,
        max_residual=0.25,
    ):
        super().__init__()
        self.base_actor = base_actor
        self.encoder = SpatioTemporalEncoder(
            history_len=history_len,
            model_dim=model_dim,
            num_heads=num_heads,
        )
        self.residual_head = nn.Sequential(
            nn.Linear(model_dim, model_dim),
            nn.ReLU(),
            nn.Linear(model_dim, action_dim),
            nn.Tanh(),
        )
        self.gate_head = nn.Linear(model_dim, 1)
        nn.init.zeros_(self.gate_head.weight)
        nn.init.constant_(self.gate_head.bias, -4.0)
        self.max_residual = float(max_residual)
        self.state_dim = int(state_dim)
        self.freeze_base_actor()

    def freeze_base_actor(self):
        self.base_actor.eval()
        for parameter in self.base_actor.parameters():
            parameter.requires_grad = False

    def train(self, mode=True):
        super().train(mode)
        self.base_actor.eval()
        return self

    def forward(self, history, return_details=False):
        base_action = self.base_actor(history[:, -1, : self.state_dim])
        features = self.encoder(history)
        residual = self.max_residual * self.residual_head(features)
        gate = torch.sigmoid(self.gate_head(features))
        action = torch.clamp(base_action + gate * residual, -1.0, 1.0)
        if return_details:
            return action, gate, residual
        return action


class AttentionQNetwork(nn.Module):
    def __init__(
        self,
        history_len=6,
        action_dim=2,
        model_dim=96,
        num_heads=4,
    ):
        super().__init__()
        self.encoder = SpatioTemporalEncoder(
            history_len=history_len,
            model_dim=model_dim,
            num_heads=num_heads,
        )
        self.value = nn.Sequential(
            nn.Linear(model_dim + action_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
        )

    def forward(self, history, action):
        features = self.encoder(history)
        return self.value(torch.cat((features, action), dim=-1))


class TwinAttentionCritic(nn.Module):
    def __init__(self, **kwargs):
        super().__init__()
        self.q1 = AttentionQNetwork(**kwargs)
        self.q2 = AttentionQNetwork(**kwargs)

    def forward(self, history, action):
        return self.q1(history, action), self.q2(history, action)

    def first(self, history, action):
        return self.q1(history, action)


class SpatioTemporalTD3:
    def __init__(
        self,
        base_actor_state,
        history_len=6,
        state_dim=24,
        action_dim=2,
        model_dim=96,
        num_heads=4,
        max_residual=0.25,
        actor_lr=1e-5,
        critic_lr=2e-5,
        device=None,
    ):
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        base_actor = BaseActor(state_dim, action_dim)
        base_actor.load_state_dict(base_actor_state)
        self.actor = ResidualAttentionActor(
            base_actor,
            history_len=history_len,
            state_dim=state_dim,
            action_dim=action_dim,
            model_dim=model_dim,
            num_heads=num_heads,
            max_residual=max_residual,
        ).to(self.device)
        self.actor_target = copy.deepcopy(self.actor).to(self.device)
        self.critic = TwinAttentionCritic(
            history_len=history_len,
            action_dim=action_dim,
            model_dim=model_dim,
            num_heads=num_heads,
        ).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)

        actor_parameters = [p for p in self.actor.parameters() if p.requires_grad]
        self.actor_optimizer = torch.optim.Adam(actor_parameters, lr=actor_lr)
        self.critic_optimizer = torch.optim.Adam(
            self.critic.parameters(), lr=critic_lr
        )
        self.actor_lr = float(actor_lr)
        self.total_updates = 0

    def select_action(self, history):
        history_tensor = torch.as_tensor(
            history, dtype=torch.float32, device=self.device
        ).unsqueeze(0)
        self.actor.eval()
        with torch.no_grad():
            action = self.actor(history_tensor)
        self.actor.train()
        return action.cpu().numpy().reshape(-1)

    def train_step(
        self,
        replay_buffer,
        batch_size=64,
        discount=0.999,
        tau=0.005,
        policy_noise=0.1,
        noise_clip=0.25,
        policy_delay=2,
        actor_start_step=5000,
        actor_lr_warmup_steps=10000,
        actor_lr_decay_steps=100000,
        actor_lr_min_ratio=0.1,
        reward_scale=0.1,
        correction_budget=0.4,
        correction_budget_penalty_weight=0.1,
        standard_correction_penalty_weight=0.25,
        standard_group="standard",
        gradient_clip=1.0,
        environment_step=0,
    ):
        if not 0.0 <= correction_budget <= 1.0:
            raise ValueError("correction_budget must be between 0 and 1")
        if correction_budget_penalty_weight < 0.0:
            raise ValueError("correction_budget_penalty_weight must be non-negative")
        if standard_correction_penalty_weight < 0.0:
            raise ValueError("standard_correction_penalty_weight must be non-negative")

        (
            histories,
            actions,
            rewards,
            dones,
            next_histories,
            groups,
        ) = replay_buffer.sample(batch_size)
        history = torch.as_tensor(histories, device=self.device)
        action = torch.as_tensor(actions, device=self.device)
        reward = torch.as_tensor(rewards, device=self.device) * reward_scale
        done = torch.as_tensor(dones, device=self.device)
        next_history = torch.as_tensor(next_histories, device=self.device)

        with torch.no_grad():
            noise = torch.randn_like(action) * policy_noise
            noise = noise.clamp(-noise_clip, noise_clip)
            next_action = (self.actor_target(next_history) + noise).clamp(-1.0, 1.0)
            target_q1, target_q2 = self.critic_target(next_history, next_action)
            target_q = reward + (1.0 - done) * discount * torch.min(
                target_q1, target_q2
            )

        current_q1, current_q2 = self.critic(history, action)
        critic_loss = F.mse_loss(current_q1, target_q) + F.mse_loss(
            current_q2, target_q
        )
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        critic_grad_norm = torch.nn.utils.clip_grad_norm_(
            self.critic.parameters(), gradient_clip
        )
        self.critic_optimizer.step()

        self.total_updates += 1
        actor_loss_value = None
        actor_grad_norm = None
        actor_metrics = {}
        actor_ready = environment_step >= actor_start_step
        if actor_ready and self.total_updates % policy_delay == 0:
            actor_lr = self._actor_learning_rate(
                environment_step,
                actor_start_step,
                actor_lr_warmup_steps,
                actor_lr_decay_steps,
                actor_lr_min_ratio,
            )
            for group in self.actor_optimizer.param_groups:
                group["lr"] = actor_lr

            self._set_requires_grad(self.critic, False)
            try:
                actor_action, gate, residual = self.actor(history, return_details=True)
                actor_q = self.critic.first(history, actor_action)
                q_normalizer = actor_q.detach().abs().mean().clamp(min=1.0)
                policy_loss = -actor_q.mean() / q_normalizer
                correction = gate * residual
                normalized_correction = correction / self.actor.max_residual
                correction_budget_penalty = F.relu(
                    normalized_correction.abs() - correction_budget
                ).pow(2).mean()
                standard_mask = torch.as_tensor(
                    groups == standard_group, device=self.device, dtype=torch.bool
                )
                if standard_mask.any():
                    standard_correction_penalty = normalized_correction[
                        standard_mask
                    ].pow(2).mean()
                else:
                    standard_correction_penalty = correction.new_zeros(())
                actor_loss = (
                    policy_loss
                    + correction_budget_penalty_weight
                    * correction_budget_penalty
                    + standard_correction_penalty_weight
                    * standard_correction_penalty
                )
                self.actor_optimizer.zero_grad()
                actor_loss.backward()
                actor_grad_norm = torch.nn.utils.clip_grad_norm_(
                    (p for p in self.actor.parameters() if p.requires_grad),
                    gradient_clip,
                )
                self.actor_optimizer.step()
            finally:
                self._set_requires_grad(self.critic, True)
            actor_loss_value = float(actor_loss.detach().cpu())
            actor_metrics = {
                "policy_loss": float(policy_loss.detach().cpu()),
                "correction_budget_penalty": float(
                    correction_budget_penalty.detach().cpu()
                ),
                "standard_correction_penalty": float(
                    standard_correction_penalty.detach().cpu()
                ),
                "correction_abs_mean": float(correction.detach().abs().mean().cpu()),
                "correction_abs_max": float(correction.detach().abs().max().cpu()),
                "actor_q_abs_mean": float(actor_q.detach().abs().mean().cpu()),
                "actor_lr": actor_lr,
            }
            actor_metrics.update(
                self._group_actor_metrics(gate, residual, correction, groups)
            )

            self._soft_update(self.actor, self.actor_target, tau)

        self._soft_update(self.critic, self.critic_target, tau)
        return {
            "critic_loss": float(critic_loss.detach().cpu()),
            "actor_loss": actor_loss_value,
            "critic_grad_norm": float(critic_grad_norm.detach().cpu()),
            "actor_grad_norm": (
                None
                if actor_grad_norm is None
                else float(actor_grad_norm.detach().cpu())
            ),
            **actor_metrics,
        }

    def _actor_learning_rate(
        self,
        environment_step,
        actor_start_step,
        warmup_steps,
        decay_steps,
        min_ratio,
    ):
        elapsed = max(environment_step - actor_start_step, 0)
        if elapsed < warmup_steps:
            return self.actor_lr * elapsed / max(float(warmup_steps), 1.0)
        decay_progress = min(
            max(elapsed - warmup_steps, 0) / max(float(decay_steps), 1.0), 1.0
        )
        cosine = 0.5 * (1.0 + math.cos(math.pi * decay_progress))
        return self.actor_lr * (min_ratio + (1.0 - min_ratio) * cosine)

    @staticmethod
    def _group_actor_metrics(gate, residual, correction, groups):
        metrics = {}
        gate = gate.detach()
        residual = residual.detach()
        correction = correction.detach()
        for group in dict.fromkeys(groups.tolist()):
            mask = torch.as_tensor(groups == group, device=gate.device)
            if not mask.any():
                continue
            group_gate = gate[mask]
            for statistic, value in (
                ("mean", group_gate.mean()),
                ("std", group_gate.std(unbiased=False)),
                ("min", group_gate.min()),
                ("max", group_gate.max()),
            ):
                metrics[f"{group}_gate_{statistic}"] = float(value.cpu())
            for index, action_name in enumerate(("linear", "angular")):
                values = residual[mask, index]
                for statistic, value in (
                    ("mean", values.mean()),
                    ("std", values.std(unbiased=False)),
                    ("min", values.min()),
                    ("max", values.max()),
                ):
                    metrics[
                        f"{group}_residual_{action_name}_{statistic}"
                    ] = float(value.cpu())
                values = correction[mask, index]
                for statistic, value in (
                    ("mean", values.mean()),
                    ("std", values.std(unbiased=False)),
                    ("min", values.min()),
                    ("max", values.max()),
                ):
                    metrics[
                        f"{group}_correction_{action_name}_{statistic}"
                    ] = float(value.cpu())
        return metrics

    @staticmethod
    def _soft_update(source, target, tau):
        for source_parameter, target_parameter in zip(
            source.parameters(), target.parameters()
        ):
            target_parameter.data.mul_(1.0 - tau)
            target_parameter.data.add_(tau * source_parameter.data)

    @staticmethod
    def _set_requires_grad(module, enabled):
        for parameter in module.parameters():
            parameter.requires_grad = enabled

    def state_dict(self):
        return {
            "actor": self.actor.state_dict(),
            "actor_target": self.actor_target.state_dict(),
            "critic": self.critic.state_dict(),
            "critic_target": self.critic_target.state_dict(),
            "actor_optimizer": self.actor_optimizer.state_dict(),
            "critic_optimizer": self.critic_optimizer.state_dict(),
            "actor_lr": self.actor_lr,
            "total_updates": self.total_updates,
        }

    def load_state_dict(self, state):
        self.actor.load_state_dict(state["actor"])
        self.actor_target.load_state_dict(state["actor_target"])
        self.critic.load_state_dict(state["critic"])
        self.critic_target.load_state_dict(state["critic_target"])
        self.actor_optimizer.load_state_dict(state["actor_optimizer"])
        self.critic_optimizer.load_state_dict(state["critic_optimizer"])
        self.actor_lr = float(state["actor_lr"])
        self.total_updates = int(state["total_updates"])
