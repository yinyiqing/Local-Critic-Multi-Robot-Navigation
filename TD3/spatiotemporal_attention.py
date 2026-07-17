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

    def action_logits(self, state):
        state = F.relu(self.layer_1(state))
        state = F.relu(self.layer_2(state))
        return self.layer_3(state)

    def forward(self, state):
        return torch.tanh(self.action_logits(state))


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


class StagedAttentionActor(nn.Module):
    def __init__(
        self,
        base_actor,
        history_len=6,
        state_dim=24,
        action_dim=2,
        model_dim=96,
        num_heads=4,
        attention_logit_scale=3.0,
        initial_gate=0.1,
    ):
        super().__init__()
        if not 0.0 < initial_gate < 1.0:
            raise ValueError("initial_gate must be between 0 and 1")
        if attention_logit_scale <= 0.0:
            raise ValueError("attention_logit_scale must be positive")
        self.base_actor = base_actor
        self.encoder = SpatioTemporalEncoder(
            history_len=history_len,
            model_dim=model_dim,
            num_heads=num_heads,
        )
        self.attention_head = nn.Sequential(
            nn.Linear(model_dim, model_dim),
            nn.ReLU(),
            nn.Linear(model_dim, action_dim),
        )
        nn.init.zeros_(self.attention_head[2].weight)
        nn.init.zeros_(self.attention_head[2].bias)
        self.gate_head = nn.Linear(model_dim, 1)
        nn.init.zeros_(self.gate_head.weight)
        gate_logit = math.log(initial_gate / (1.0 - initial_gate))
        nn.init.constant_(self.gate_head.bias, gate_logit)
        self.attention_logit_scale = float(attention_logit_scale)
        self.state_dim = int(state_dim)

    def forward(self, history, attention_enabled=True, return_details=False):
        base_logits = self.base_actor.action_logits(
            history[:, -1, : self.state_dim]
        )
        base_action = torch.tanh(base_logits)
        if not attention_enabled and not return_details:
            return base_action

        features = self.encoder(history)
        attention_delta = self.attention_logit_scale * torch.tanh(
            self.attention_head(features)
        )
        attention_action = torch.tanh(base_logits + attention_delta)
        gate_logits = self.gate_head(features)
        learned_gate = torch.sigmoid(gate_logits)
        effective_gate = (
            learned_gate if attention_enabled else torch.zeros_like(learned_gate)
        )
        action = torch.lerp(base_action, attention_action, effective_gate)
        if return_details:
            return (
                action,
                base_action,
                attention_action,
                learned_gate,
                gate_logits,
            )
        return action


class HistoryMLPQNetwork(nn.Module):
    def __init__(
        self,
        history_len=6,
        state_dim=24,
        action_dim=2,
        hidden_dim=256,
    ):
        super().__init__()
        self.history_len = int(history_len)
        self.state_dim = int(state_dim)
        input_dim = self.history_len * self.state_dim + int(action_dim)
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, history, action):
        if history.ndim != 3:
            raise ValueError("history must have shape [batch, time, state]")
        batch_size, time_steps, state_dim = history.shape
        if time_steps != self.history_len or state_dim != self.state_dim:
            raise ValueError(
                "expected history shape [batch, %d, %d], got %s"
                % (self.history_len, self.state_dim, tuple(history.shape))
            )
        flattened_history = history.reshape(batch_size, self.history_len * self.state_dim)
        return self.net(torch.cat((flattened_history, action), dim=-1))


class TwinHistoryMLPCritic(nn.Module):
    def __init__(self, **kwargs):
        super().__init__()
        self.q1 = HistoryMLPQNetwork(**kwargs)
        self.q2 = HistoryMLPQNetwork(**kwargs)

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
        attention_logit_scale=3.0,
        initial_gate=0.1,
        base_actor_lr=1e-5,
        attention_lr=1e-5,
        critic_lr=2e-5,
        critic_hidden_dim=256,
        device=None,
    ):
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        base_actor = BaseActor(state_dim, action_dim)
        base_actor.load_state_dict(base_actor_state)
        self.actor = StagedAttentionActor(
            base_actor,
            history_len=history_len,
            state_dim=state_dim,
            action_dim=action_dim,
            model_dim=model_dim,
            num_heads=num_heads,
            attention_logit_scale=attention_logit_scale,
            initial_gate=initial_gate,
        ).to(self.device)
        self.actor_target = copy.deepcopy(self.actor).to(self.device)
        self.critic = TwinHistoryMLPCritic(
            history_len=history_len,
            state_dim=state_dim,
            action_dim=action_dim,
            hidden_dim=critic_hidden_dim,
        ).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)

        attention_parameters = list(self.actor.encoder.parameters())
        attention_parameters.extend(self.actor.attention_head.parameters())
        attention_parameters.extend(self.actor.gate_head.parameters())
        self.actor_optimizer = torch.optim.Adam(
            [
                {
                    "params": self.actor.base_actor.parameters(),
                    "lr": base_actor_lr,
                    "name": "base",
                },
                {
                    "params": attention_parameters,
                    "lr": 0.0,
                    "name": "attention",
                },
            ]
        )
        self.critic_optimizer = torch.optim.Adam(
            self.critic.parameters(), lr=critic_lr
        )
        self.base_actor_lr = float(base_actor_lr)
        self.attention_lr = float(attention_lr)
        self.attention_enabled = False
        self.total_updates = 0

    def set_attention_enabled(self, enabled):
        self.attention_enabled = bool(enabled)

    def select_action(self, history, attention_enabled=None):
        history_tensor = torch.as_tensor(
            history, dtype=torch.float32, device=self.device
        ).unsqueeze(0)
        self.actor.eval()
        with torch.no_grad():
            action = self.actor(
                history_tensor,
                attention_enabled=(
                    self.attention_enabled
                    if attention_enabled is None
                    else bool(attention_enabled)
                ),
            )
        self.actor.train()
        return action.cpu().numpy().reshape(-1)

    def train_step(
        self,
        replay_buffer,
        batch_size=96,
        discount=0.999,
        tau=0.005,
        policy_noise=0.1,
        noise_clip=0.25,
        policy_delay=2,
        actor_start_step=5000,
        attention_start_step=100000,
        actor_lr_warmup_steps=10000,
        actor_lr_decay_steps=100000,
        actor_lr_min_ratio=0.1,
        base_finetune_lr_ratio=0.1,
        gate_supervision_weight=1.0,
        reward_scale=0.1,
        gradient_clip=1.0,
        environment_step=0,
    ):
        if attention_start_step <= actor_start_step:
            raise ValueError(
                "attention_start_step must be greater than actor_start_step"
            )
        if not 0.0 <= base_finetune_lr_ratio <= 1.0:
            raise ValueError("base_finetune_lr_ratio must be between 0 and 1")
        if gate_supervision_weight < 0.0:
            raise ValueError("gate_supervision_weight must be non-negative")

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

        attention_enabled = environment_step >= attention_start_step
        self.set_attention_enabled(attention_enabled)

        with torch.no_grad():
            noise = torch.randn_like(action) * policy_noise
            noise = noise.clamp(-noise_clip, noise_clip)
            next_action = (
                self.actor_target(
                    next_history, attention_enabled=attention_enabled
                )
                + noise
            ).clamp(-1.0, 1.0)
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
            if attention_enabled:
                attention_lr = self._actor_learning_rate(
                    environment_step,
                    attention_start_step,
                    actor_lr_warmup_steps,
                    actor_lr_decay_steps,
                    actor_lr_min_ratio,
                    self.attention_lr,
                )
                base_lr = (
                    attention_lr
                    * self.base_actor_lr
                    / self.attention_lr
                    * base_finetune_lr_ratio
                )
            else:
                attention_lr = 0.0
                base_lr = self._actor_learning_rate(
                    environment_step,
                    actor_start_step,
                    actor_lr_warmup_steps,
                    actor_lr_decay_steps,
                    actor_lr_min_ratio,
                    self.base_actor_lr,
                )
            self._set_actor_learning_rates(base_lr, attention_lr)

            self._set_requires_grad(self.critic, False)
            try:
                (
                    actor_action,
                    base_action,
                    attention_action,
                    gate,
                    gate_logits,
                ) = self.actor(
                    history,
                    attention_enabled=attention_enabled,
                    return_details=True,
                )
                actor_q = self.critic.first(history, actor_action)
                q_normalizer = actor_q.detach().abs().mean().clamp(min=1.0)
                policy_loss = -actor_q.mean() / q_normalizer
                if attention_enabled:
                    gate_targets = self._gate_targets(groups, gate_logits.device)
                    gate_loss = F.binary_cross_entropy_with_logits(
                        gate_logits, gate_targets
                    )
                else:
                    gate_loss = torch.zeros((), device=self.device)
                actor_loss = policy_loss + gate_supervision_weight * gate_loss
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
                "gate_supervision_loss": float(gate_loss.detach().cpu()),
                "actor_q_abs_mean": float(actor_q.detach().abs().mean().cpu()),
                "base_actor_lr": base_lr,
                "attention_lr": attention_lr,
                "attention_enabled": float(attention_enabled),
            }
            actor_metrics.update(
                self._group_actor_metrics(
                    gate, base_action, attention_action, groups
                )
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
        peak_lr,
    ):
        elapsed = max(environment_step - actor_start_step, 0)
        if elapsed < warmup_steps:
            return peak_lr * elapsed / max(float(warmup_steps), 1.0)
        decay_progress = min(
            max(elapsed - warmup_steps, 0) / max(float(decay_steps), 1.0), 1.0
        )
        cosine = 0.5 * (1.0 + math.cos(math.pi * decay_progress))
        return peak_lr * (min_ratio + (1.0 - min_ratio) * cosine)

    def _set_actor_learning_rates(self, base_lr, attention_lr):
        for group in self.actor_optimizer.param_groups:
            if group["name"] == "base":
                group["lr"] = base_lr
            elif group["name"] == "attention":
                group["lr"] = attention_lr

    @staticmethod
    def _gate_targets(groups, device):
        unknown = sorted(set(groups.tolist()) - {"standard", "dense"})
        if unknown:
            raise ValueError(f"Unsupported gate supervision groups: {unknown}")
        return torch.as_tensor(
            (groups == "dense").astype("float32"), device=device
        ).unsqueeze(1)

    @staticmethod
    def _group_actor_metrics(gate, base_action, attention_action, groups):
        metrics = {}
        gate = gate.detach()
        base_action = base_action.detach()
        attention_action = attention_action.detach()
        correction = gate * (attention_action - base_action)
        for group in ("standard", "dense"):
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
                values = attention_action[mask, index]
                for statistic, value in (
                    ("mean", values.mean()),
                    ("std", values.std(unbiased=False)),
                    ("min", values.min()),
                    ("max", values.max()),
                ):
                    metrics[
                        f"{group}_attention_action_{action_name}_{statistic}"
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
            "base_actor_lr": self.base_actor_lr,
            "attention_lr": self.attention_lr,
            "attention_enabled": self.attention_enabled,
            "total_updates": self.total_updates,
        }

    def load_state_dict(self, state):
        self.actor.load_state_dict(state["actor"])
        self.actor_target.load_state_dict(state["actor_target"])
        self.critic.load_state_dict(state["critic"])
        self.critic_target.load_state_dict(state["critic_target"])
        self.actor_optimizer.load_state_dict(state["actor_optimizer"])
        self.critic_optimizer.load_state_dict(state["critic_optimizer"])
        self.base_actor_lr = float(state["base_actor_lr"])
        self.attention_lr = float(state["attention_lr"])
        self.attention_enabled = bool(state.get("attention_enabled", False))
        self.total_updates = int(state["total_updates"])
