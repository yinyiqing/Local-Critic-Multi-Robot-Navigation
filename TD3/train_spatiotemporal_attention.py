import os
import random
import socket
import time
from collections import deque
from datetime import datetime

import numpy as np
import torch
from torch.utils.tensorboard import SummaryWriter

from multi_agent_velodyne_env import MultiAgentGazeboEnv
from hard_case_sampling import (
    apply_group_balanced_hard_case_weights,
    episode_failure_signal,
    update_failure_score,
)
from scenario_manifests import load_manifest_cases
from sequence_replay_buffer import SequenceReplayBuffer
from spatiotemporal_attention import BaseActor, SpatioTemporalTD3


def env_int(name, default):
    value = os.environ.get(name)
    return default if value is None or not value.strip() else int(value)


def env_float(name, default):
    value = os.environ.get(name)
    return default if value is None or not value.strip() else float(value)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None or not value.strip():
        return bool(default)
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def make_histories(states, history_len):
    return {
        index: deque(
            [np.asarray(state, dtype=np.float32)] * history_len,
            maxlen=history_len,
        )
        for index, state in enumerate(states)
    }


def history_array(histories, index):
    return np.stack(histories[index]).astype(np.float32, copy=False)


def policy_action_to_env(raw_action, forward_speed):
    raw_action = np.asarray(raw_action, dtype=np.float32)
    linear = np.clip(
        (raw_action[0] + 1.0) * 0.5 * forward_speed,
        0.0,
        forward_speed,
    )
    return [float(linear), float(raw_action[1])]


class FrozenBasePolicy:
    """Immutable 5D Actor used as the fixed benchmark and actor anchor source."""

    def __init__(self, state_dict, device):
        self.device = device
        self.actor = BaseActor().to(self.device)
        self.actor.load_state_dict(state_dict)
        self.actor.eval()

    def select_action(self, history, attention_enabled=None):
        state = torch.as_tensor(
            history[-1], dtype=torch.float32, device=self.device
        ).unsqueeze(0)
        with torch.no_grad():
            action = self.actor(state)
        return action.cpu().numpy().reshape(-1)


def local_driving_shaping(
    next_state,
    env_action,
    slowdown_distance,
    slowdown_penalty_weight,
    forward_speed,
):
    min_laser = float(np.min(np.asarray(next_state)[:20]))
    pressure = np.clip(
        (slowdown_distance - min_laser) / max(slowdown_distance, 1e-6),
        0.0,
        1.0,
    )
    linear = float(env_action[0])
    safe_forward = forward_speed * (1.0 - pressure)
    overspeed = max(linear - safe_forward, 0.0)
    return float(-slowdown_penalty_weight * overspeed**2)


def evaluate_group(
    agent,
    env,
    evaluation_cases,
    group,
    history_len,
    episodes,
    max_episode_steps,
    evaluation_seed,
    forward_speed,
    attention_enabled=None,
):
    original_cases = env.curriculum_cases
    original_index = env.curriculum_case_index
    original_case = env.current_curriculum_case
    original_sampling = os.environ.get("DRL_MULTI_MANIFEST_SAMPLING")
    original_upper = env.upper
    original_lower = env.lower
    random_state = random.getstate()
    numpy_state = np.random.get_state()
    torch_state = torch.get_rng_state()
    cuda_states = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
    group_cases = [case for case in evaluation_cases if case.get("group") == group]
    if not group_cases:
        raise ValueError(f"No validation manifest cases found for group: {group}")

    episodes = int(episodes)
    successes = 0
    collisions = 0
    full_successes = 0
    timeouts = 0
    initial_goal_distances = []
    total_agents = episodes * env.num_agents
    try:
        env.curriculum_cases = group_cases
        env.curriculum_case_index = 0
        os.environ["DRL_MULTI_MANIFEST_SAMPLING"] = "cycle"
        env.upper = 10.0
        env.lower = -10.0
        random.seed(evaluation_seed)
        np.random.seed(evaluation_seed)
        torch.manual_seed(evaluation_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(evaluation_seed)
        for _ in range(episodes):
            states = env.reset()
            scenario_id = env.current_scenario_id()
            initial_goal_distances.extend(float(state[20]) for state in states)
            histories = make_histories(states, history_len)
            active = [True] * env.num_agents
            episode_success = np.zeros(env.num_agents, dtype=np.int32)
            episode_collision = np.zeros(env.num_agents, dtype=np.int32)
            for step in range(max_episode_steps):
                actions = []
                for index in range(env.num_agents):
                    if not active[index]:
                        actions.append([0.0, 0.0])
                        continue
                    raw_action = agent.select_action(
                        history_array(histories, index),
                        attention_enabled=attention_enabled,
                    )
                    actions.append(policy_action_to_env(raw_action, forward_speed))
                next_states, _, dones, targets, collision_flags = env.step(
                    actions, active
                )
                for index, next_state in enumerate(next_states):
                    histories[index].append(np.asarray(next_state, dtype=np.float32))
                    if not active[index]:
                        continue
                    episode_success[index] = max(
                        episode_success[index], int(targets[index])
                    )
                    episode_collision[index] = max(
                        episode_collision[index], int(collision_flags[index])
                    )
                    if dones[index]:
                        active[index] = False
                if not any(active):
                    break
            else:
                timeouts += 1
            successes += int(episode_success.sum())
            collisions += int(episode_collision.sum())
            full_successes += int(episode_success.sum() == env.num_agents)
            print(
                "Eval scenario | group=%s | scenario_id=%s | success=%d/%d | "
                "collision=%d/%d | full=%d"
                % (
                    group,
                    scenario_id,
                    int(episode_success.sum()),
                    env.num_agents,
                    int(episode_collision.sum()),
                    env.num_agents,
                    int(episode_success.sum() == env.num_agents),
                )
            )
    finally:
        env.curriculum_cases = original_cases
        env.curriculum_case_index = original_index
        env.current_curriculum_case = original_case
        env.upper = original_upper
        env.lower = original_lower
        if original_sampling is None:
            os.environ.pop("DRL_MULTI_MANIFEST_SAMPLING", None)
        else:
            os.environ["DRL_MULTI_MANIFEST_SAMPLING"] = original_sampling
        random.setstate(random_state)
        np.random.set_state(numpy_state)
        torch.set_rng_state(torch_state)
        if cuda_states is not None:
            torch.cuda.set_rng_state_all(cuda_states)

    return {
        "success_rate": successes / total_agents,
        "collision_rate": collisions / total_agents,
        "full_success_rate": full_successes / episodes,
        "timeout_rate": timeouts / episodes,
        "initial_goal_distance_mean": float(np.mean(initial_goal_distances)),
    }


def best_key(standard, dense):
    return (
        min(standard["full_success_rate"], dense["full_success_rate"]),
        (standard["full_success_rate"] + dense["full_success_rate"]) / 2.0,
        (standard["success_rate"] + dense["success_rate"]) / 2.0,
        -(standard["collision_rate"] + dense["collision_rate"]) / 2.0,
    )


seed = env_int("DRL_ATTENTION_SEED", 0)
history_len = env_int("DRL_ATTENTION_HISTORY_LEN", 6)
model_dim = env_int("DRL_ATTENTION_MODEL_DIM", 96)
num_heads = env_int("DRL_ATTENTION_NUM_HEADS", 4)
attention_logit_scale = env_float("DRL_ATTENTION_LOGIT_SCALE", 0.5)
initial_gate = env_float("DRL_ATTENTION_INITIAL_GATE", 0.1)
gate_temperature = env_float("DRL_ATTENTION_GATE_TEMPERATURE", 0.5)
base_actor_lr = env_float("DRL_ATTENTION_BASE_ACTOR_LR", 1e-5)
attention_lr = env_float("DRL_ATTENTION_LR", 1e-5)
critic_lr = env_float("DRL_ATTENTION_CRITIC_LR", 2e-5)
critic_hidden_dim = env_int("DRL_ATTENTION_CRITIC_HIDDEN_DIM", 256)
actor_start_step = env_int("DRL_ATTENTION_ACTOR_START_STEP", 20000)
attention_start_step = env_int("DRL_ATTENTION_START_STEP", 30000)
actor_lr_warmup_steps = env_int("DRL_ATTENTION_ACTOR_WARMUP_STEPS", 10000)
actor_lr_decay_steps = env_int("DRL_ATTENTION_ACTOR_DECAY_STEPS", 100000)
actor_lr_min_ratio = env_float("DRL_ATTENTION_ACTOR_MIN_LR_RATIO", 0.1)
base_finetune_lr_ratio = env_float("DRL_ATTENTION_BASE_FINETUNE_LR_RATIO", 0.0)
attention_base_warmup_steps = env_int("DRL_ATTENTION_BASE_WARMUP_STEPS", 10000)
gate_supervision_weight = env_float("DRL_ATTENTION_GATE_LOSS_WEIGHT", 0.5)
gate_positive_weight = env_float("DRL_ATTENTION_GATE_POSITIVE_WEIGHT", 4.0)
gate_safe_sparsity_weight = env_float("DRL_ATTENTION_GATE_SAFE_SPARSITY", 0.01)
actor_anchor_weight = env_float("DRL_ATTENTION_ACTOR_ANCHOR_WEIGHT", 5.0)
attention_correction_weight = env_float(
    "DRL_ATTENTION_CORRECTION_WEIGHT", 1.0
)
discount = env_float("DRL_ATTENTION_DISCOUNT", 0.99)
exploration_noise = env_float("DRL_ATTENTION_EXPLORATION_NOISE", 0.1)
gradient_clip = env_float("DRL_ATTENTION_GRADIENT_CLIP", 1.0)
reward_scale = env_float("DRL_ATTENTION_REWARD_SCALE", 0.1)
forward_speed = env_float("DRL_ATTENTION_FORWARD_SPEED", 1.0)
slowdown_distance = env_float("DRL_ATTENTION_SLOWDOWN_DISTANCE", 1.8)
slowdown_penalty_weight = env_float("DRL_ATTENTION_SLOWDOWN_PENALTY", 2.0)
robot_safe_distance = env_float("DRL_ATTENTION_ROBOT_SAFE_DISTANCE", 0.8)
team_completion_bonus = env_float("DRL_ATTENTION_TEAM_COMPLETION_BONUS", 5.0)
team_progress_bonus = env_float("DRL_ATTENTION_TEAM_PROGRESS_BONUS", 1.0)
interaction_risk_visible_range = env_float(
    "DRL_ATTENTION_RISK_VISIBLE_RANGE", 4.0
)
interaction_risk_distance = env_float("DRL_ATTENTION_RISK_DISTANCE", 1.5)
interaction_risk_ttc_horizon = env_float("DRL_ATTENTION_RISK_TTC_HORIZON", 2.0)
hard_case_sampling_start_step = env_int(
    "DRL_ATTENTION_HARD_CASE_START_STEP",
    attention_start_step + attention_base_warmup_steps,
)
hard_case_sampling_strength = env_float("DRL_ATTENTION_HARD_CASE_STRENGTH", 1.5)
hard_case_uniform_fraction = env_float("DRL_ATTENTION_HARD_CASE_UNIFORM_FRACTION", 0.3)
hard_case_score_ema = env_float("DRL_ATTENTION_HARD_CASE_SCORE_EMA", 0.9)
batch_size = env_int("DRL_ATTENTION_BATCH_SIZE", 96)
replay_capacity = env_int("DRL_ATTENTION_REPLAY_CAPACITY", 200000)
replay_group_ratios = {
    "standard": env_float("DRL_ATTENTION_REPLAY_STANDARD_RATIO", 1.0),
    "dense": env_float("DRL_ATTENTION_REPLAY_DENSE_RATIO", 1.0),
}
learning_starts = env_int("DRL_ATTENTION_LEARNING_STARTS", 2000)
max_episodes = env_int("DRL_ATTENTION_MAX_EPISODES", 1000)
max_episode_steps = env_int("DRL_ATTENTION_MAX_EPISODE_STEPS", 300)
eval_interval = env_int("DRL_ATTENTION_EVAL_INTERVAL", 25)
standard_eval_episodes = env_int("DRL_ATTENTION_STANDARD_EVAL_EPISODES", 30)
dense_eval_episodes = env_int("DRL_ATTENTION_DENSE_EVAL_EPISODES", 30)
evaluation_seed = env_int("DRL_ATTENTION_EVAL_SEED", 20260713)
early_stopping_patience = env_int("DRL_ATTENTION_EARLY_STOPPING_PATIENCE", 8)
checkpoint_interval = env_int("DRL_ATTENTION_CHECKPOINT_INTERVAL", 10)
startup_odom_timeout = env_float("DRL_ATTENTION_STARTUP_ODOM_TIMEOUT", 240.0)
resume_training = env_bool("DRL_ATTENTION_RESUME", False)


def validate_training_config():
    if history_len <= 0:
        raise ValueError("DRL_ATTENTION_HISTORY_LEN must be positive")
    if model_dim <= 0 or num_heads <= 0 or model_dim % num_heads != 0:
        raise ValueError(
            "DRL_ATTENTION_MODEL_DIM must be positive and divisible by "
            "DRL_ATTENTION_NUM_HEADS"
        )
    if attention_logit_scale <= 0.0:
        raise ValueError("DRL_ATTENTION_LOGIT_SCALE must be positive")
    if not 0.0 < initial_gate < 1.0:
        raise ValueError("DRL_ATTENTION_INITIAL_GATE must be between 0 and 1")
    if gate_temperature <= 0.0:
        raise ValueError("DRL_ATTENTION_GATE_TEMPERATURE must be positive")
    if min(base_actor_lr, attention_lr, critic_lr) <= 0.0:
        raise ValueError("Actor, Attention, and Critic learning rates must be positive")
    if critic_hidden_dim < 2:
        raise ValueError("DRL_ATTENTION_CRITIC_HIDDEN_DIM must be at least 2")
    if min(actor_start_step, actor_lr_warmup_steps, attention_base_warmup_steps) < 0:
        raise ValueError("Attention actor start and warmup steps must be non-negative")
    if attention_start_step <= actor_start_step:
        raise ValueError(
            "DRL_ATTENTION_START_STEP must be greater than "
            "DRL_ATTENTION_ACTOR_START_STEP"
        )
    if actor_lr_decay_steps <= 0:
        raise ValueError("DRL_ATTENTION_ACTOR_DECAY_STEPS must be positive")
    if not 0.0 <= actor_lr_min_ratio <= 1.0:
        raise ValueError("DRL_ATTENTION_ACTOR_MIN_LR_RATIO must be between 0 and 1")
    if not 0.0 <= base_finetune_lr_ratio <= 1.0:
        raise ValueError(
            "DRL_ATTENTION_BASE_FINETUNE_LR_RATIO must be between 0 and 1"
        )
    if base_finetune_lr_ratio != 0.0:
        raise ValueError(
            "Causal Attention training keeps the base Actor frozen after "
            "DRL_ATTENTION_START_STEP; set DRL_ATTENTION_BASE_FINETUNE_LR_RATIO=0"
        )
    if (
        min(
            gate_supervision_weight,
            gate_safe_sparsity_weight,
            actor_anchor_weight,
            attention_correction_weight,
            robot_safe_distance,
            team_completion_bonus,
            team_progress_bonus,
        ) < 0.0
        or gate_positive_weight <= 0.0
    ):
        raise ValueError("Attention regularization weights must be non-negative")
    if not 0.0 < discount < 1.0:
        raise ValueError("DRL_ATTENTION_DISCOUNT must be between 0 and 1")
    if exploration_noise < 0.0 or gradient_clip <= 0.0 or reward_scale <= 0.0:
        raise ValueError(
            "Exploration noise must be non-negative; gradient clip and reward "
            "scale must be positive"
        )
    if min(forward_speed, slowdown_distance) <= 0.0:
        raise ValueError("Forward speed limit and slowdown distance must be positive")
    if slowdown_penalty_weight < 0.0:
        raise ValueError("Local driving shaping weight must be non-negative")
    if min(
        interaction_risk_visible_range,
        interaction_risk_distance,
        interaction_risk_ttc_horizon,
    ) <= 0.0:
        raise ValueError("Interaction-risk distances and TTC horizon must be positive")
    if hard_case_sampling_start_step < attention_start_step:
        raise ValueError(
            "Hard-case sampling must begin after Attention is enabled"
        )
    if hard_case_sampling_strength < 0.0:
        raise ValueError("Hard-case sampling strength must be non-negative")
    if not 0.0 <= hard_case_uniform_fraction <= 1.0:
        raise ValueError("Hard-case uniform fraction must be between 0 and 1")
    if not 0.0 <= hard_case_score_ema < 1.0:
        raise ValueError("Hard-case score EMA must be in [0, 1)")
    if batch_size < len(replay_group_ratios):
        raise ValueError("DRL_ATTENTION_BATCH_SIZE must cover all replay groups")
    if any(ratio <= 0.0 for ratio in replay_group_ratios.values()):
        raise ValueError("All attention replay group ratios must be positive")
    if replay_capacity < batch_size or learning_starts < batch_size:
        raise ValueError(
            "Replay capacity and DRL_ATTENTION_LEARNING_STARTS must be at least "
            "DRL_ATTENTION_BATCH_SIZE"
        )
    if min(max_episodes, max_episode_steps, eval_interval) <= 0:
        raise ValueError("Episode and evaluation intervals must be positive")
    if standard_eval_episodes <= 0 or dense_eval_episodes <= 0:
        raise ValueError("Attention evaluation sample counts must be positive")
    if checkpoint_interval <= 0 or early_stopping_patience < 0:
        raise ValueError(
            "Checkpoint interval must be positive and early-stopping patience "
            "must be non-negative"
        )
    if startup_odom_timeout <= 0.0:
        raise ValueError("DRL_ATTENTION_STARTUP_ODOM_TIMEOUT must be positive")


validate_training_config()

agent_names = [f"r{index}" for index in range(1, 6)]
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
manifest_root = os.path.join(project_root, "fixed_scenarios_v1", "data", "fixed_v1")
default_train_manifests = os.pathsep.join(
    [
        os.path.join(manifest_root, "standard", "train.json.gz"),
        os.path.join(manifest_root, "dense", "train.json.gz"),
    ]
)
default_validation_manifests = os.pathsep.join(
    [
        os.path.join(manifest_root, "standard", "validation.json.gz"),
        os.path.join(manifest_root, "dense", "validation.json.gz"),
    ]
)
train_manifest_paths = os.environ.get(
    "DRL_MULTI_MANIFEST_PATHS", default_train_manifests
).strip()
validation_manifest_paths = os.environ.get(
    "DRL_ATTENTION_VALIDATION_MANIFEST_PATHS", default_validation_manifests
).strip()
os.environ["DRL_MULTI_MANIFEST_PATHS"] = train_manifest_paths
os.environ.setdefault("DRL_MULTI_MANIFEST_SAMPLING", "random")
launchfile = os.environ.get(
    "DRL_ATTENTION_LAUNCHFILE", "multi_robot_scenario_attention_5.launch"
)
base_model = os.environ.get(
    "DRL_ATTENTION_BASE_MODEL",
    "TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best",
)
model_name = "TD3_velodyne_multi_fixed_manifest_attention"
base_actor_path = os.path.join("pytorch_models", f"{base_model}_actor.pth")
checkpoint_path = os.path.join("checkpoints", f"{model_name}_latest.pt")
best_checkpoint_path = os.path.join("checkpoints", f"{model_name}_best.pt")
base_stage_actor_path = os.path.join(
    "pytorch_models", f"{model_name}_base_stage_actor.pth"
)

random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

base_actor_state = torch.load(base_actor_path, map_location="cpu", weights_only=True)
agent = SpatioTemporalTD3(
    base_actor_state,
    history_len=history_len,
    model_dim=model_dim,
    num_heads=num_heads,
    attention_logit_scale=attention_logit_scale,
    initial_gate=initial_gate,
    gate_temperature=gate_temperature,
    base_actor_lr=base_actor_lr,
    attention_lr=attention_lr,
    critic_lr=critic_lr,
    critic_hidden_dim=critic_hidden_dim,
)
reference_policy = FrozenBasePolicy(base_actor_state, agent.device)
replay_buffer = SequenceReplayBuffer(
    replay_capacity, seed, group_ratios=replay_group_ratios
)

env = MultiAgentGazeboEnv(
    launchfile,
    20,
    agent_names=agent_names,
    cooperative_reward=False,
    anti_stagnation_reward=False,
    wall_clearance_reward=False,
    local_navigation_reward=False,
    robot_safe_distance=robot_safe_distance,
    weak_coupling_layout=True,
    scenario_mode="manifest",
    active_neighbors_only=True,
    team_completion_bonus=team_completion_bonus,
    team_progress_bonus=team_progress_bonus,
    interaction_risk_visible_range=interaction_risk_visible_range,
    interaction_risk_distance=interaction_risk_distance,
    interaction_risk_ttc_horizon=interaction_risk_ttc_horizon,
)
validation_cases, validation_manifest_metadata = load_manifest_cases(
    validation_manifest_paths,
    agent_names,
)
if {item["split"] for item in env.manifest_metadata} != {"train"}:
    raise ValueError("Attention training manifests must all use the train split")
if {item["split"] for item in validation_manifest_metadata} != {"validation"}:
    raise ValueError("Attention evaluation manifests must all use the validation split")
for agent_name in agent_names:
    env.wait_for_odom(agent_name, timeout=startup_odom_timeout)
print("All robot odometry topics are ready; training may start")

timestamp = datetime.now().strftime("%b%d_%H-%M-%S")
writer = SummaryWriter(
    log_dir=os.path.join("runs", f"attention_{timestamp}_{socket.gethostname()}")
)
episode = 0
environment_steps = 0
agent_samples = 0
best_metrics = None
evaluations_without_improvement = 0
base_stage_saved = False
reference_metrics = None
attention_reference_metrics = None
case_failure_scores = {}

training_config = {
    "training_version": "causal_interaction_risk_gated",
    "seed": seed,
    "history_len": history_len,
    "model_dim": model_dim,
    "num_heads": num_heads,
    "critic_type": "full_history_mlp",
    "critic_hidden_dim": critic_hidden_dim,
    "attention_logit_scale": attention_logit_scale,
    "initial_gate": initial_gate,
    "gate_temperature": gate_temperature,
    "base_model": base_model,
    "base_actor_lr": base_actor_lr,
    "attention_lr": attention_lr,
    "critic_lr": critic_lr,
    "actor_start_step": actor_start_step,
    "attention_start_step": attention_start_step,
    "actor_lr_warmup_steps": actor_lr_warmup_steps,
    "actor_lr_decay_steps": actor_lr_decay_steps,
    "actor_lr_min_ratio": actor_lr_min_ratio,
    "base_finetune_lr_ratio": base_finetune_lr_ratio,
    "attention_base_warmup_steps": attention_base_warmup_steps,
    "gate_supervision_weight": gate_supervision_weight,
    "gate_positive_weight": gate_positive_weight,
    "gate_safe_sparsity_weight": gate_safe_sparsity_weight,
    "actor_anchor_weight": actor_anchor_weight,
    "attention_correction_weight": attention_correction_weight,
    "discount": discount,
    "reward_scale": reward_scale,
    "exploration_noise": exploration_noise,
    "gradient_clip": gradient_clip,
    "batch_size": batch_size,
    "replay_capacity": replay_capacity,
    "learning_starts": learning_starts,
    "replay_group_ratios": replay_group_ratios,
    "forward_speed": forward_speed,
    "slowdown_distance": slowdown_distance,
    "slowdown_penalty_weight": slowdown_penalty_weight,
    "robot_safe_distance": robot_safe_distance,
    "team_completion_bonus": team_completion_bonus,
    "team_progress_bonus": team_progress_bonus,
    "interaction_risk_visible_range": interaction_risk_visible_range,
    "interaction_risk_distance": interaction_risk_distance,
    "interaction_risk_ttc_horizon": interaction_risk_ttc_horizon,
    "hard_case_sampling_start_step": hard_case_sampling_start_step,
    "hard_case_sampling_strength": hard_case_sampling_strength,
    "hard_case_uniform_fraction": hard_case_uniform_fraction,
    "hard_case_score_ema": hard_case_score_ema,
    "max_episode_steps": max_episode_steps,
    "eval_interval": eval_interval,
    "standard_eval_episodes": standard_eval_episodes,
    "dense_eval_episodes": dense_eval_episodes,
    "evaluation_seed": evaluation_seed,
    "early_stopping_patience": early_stopping_patience,
    "train_manifest_dataset_ids": [
        item["dataset_id"] for item in env.manifest_metadata
    ],
    "validation_manifest_dataset_ids": [
        item["dataset_id"] for item in validation_manifest_metadata
    ],
}


def save_checkpoint(path):
    torch.save(
        {
            "agent": agent.state_dict(),
            "replay_buffer": replay_buffer.state_dict(),
            "episode": episode,
            "environment_steps": environment_steps,
            "agent_samples": agent_samples,
            "best_metrics": best_metrics,
            "evaluations_without_improvement": evaluations_without_improvement,
            "base_stage_saved": base_stage_saved,
            "reference_metrics": reference_metrics,
            "attention_reference_metrics": attention_reference_metrics,
            "case_failure_scores": case_failure_scores,
            "config": training_config,
        },
        path,
    )


if resume_training and os.path.exists(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    changed_config_keys = {
        key
        for key in set(config) | set(training_config)
        if config.get(key) != training_config.get(key)
    }
    can_adjust_attention_start = (
        changed_config_keys == {"attention_start_step"}
        and not bool(checkpoint["agent"].get("attention_enabled", False))
        and int(checkpoint["agent_samples"]) < attention_start_step
    )
    if config != training_config and not can_adjust_attention_start:
        raise ValueError(
            f"Checkpoint config mismatch: {config} != {training_config}"
        )
    if can_adjust_attention_start:
        print(
            "Resuming with attention start adjusted from %d to %d samples"
            % (int(config["attention_start_step"]), attention_start_step)
        )
    agent.load_state_dict(checkpoint["agent"])
    replay_buffer.load_state_dict(checkpoint["replay_buffer"])
    episode = int(checkpoint["episode"])
    environment_steps = int(checkpoint["environment_steps"])
    agent_samples = int(checkpoint["agent_samples"])
    best_metrics = checkpoint.get("best_metrics")
    evaluations_without_improvement = int(
        checkpoint.get("evaluations_without_improvement", 0)
    )
    base_stage_saved = bool(checkpoint.get("base_stage_saved", False))
    reference_metrics = checkpoint.get("reference_metrics")
    attention_reference_metrics = checkpoint.get("attention_reference_metrics")
    case_failure_scores = dict(checkpoint.get("case_failure_scores", {}))
    apply_group_balanced_hard_case_weights(
        env.curriculum_cases,
        case_failure_scores,
        strength=hard_case_sampling_strength,
        uniform_fraction=hard_case_uniform_fraction,
    )
    print("Resumed attention training from:", checkpoint_path)
elif os.path.exists(checkpoint_path):
    print(
        "Starting a fresh interaction-risk run; set DRL_ATTENTION_RESUME=1 "
        "only for a checkpoint created with this training configuration."
    )
    for stale_path in (
        checkpoint_path,
        best_checkpoint_path,
        f"pytorch_models/{model_name}_actor.pth",
        base_stage_actor_path,
    ):
        if os.path.exists(stale_path):
            os.remove(stale_path)
            print("Removed stale Attention artifact:", stale_path)

agent.set_attention_enabled(agent_samples >= attention_start_step)

if reference_metrics is None:
    print("Evaluating immutable 5D reference on fixed validation manifests")
    reference_metrics = {
        "standard": evaluate_group(
            reference_policy,
            env,
            validation_cases,
            "standard",
            history_len,
            standard_eval_episodes,
            max_episode_steps,
            evaluation_seed,
            forward_speed,
        ),
        "dense": evaluate_group(
            reference_policy,
            env,
            validation_cases,
            "dense",
            history_len,
            dense_eval_episodes,
            max_episode_steps,
            evaluation_seed + 1000,
            forward_speed,
        ),
    }
    print("Reference standard:", reference_metrics["standard"])
    print("Reference dense:", reference_metrics["dense"])
    for group, metrics in reference_metrics.items():
        for name, value in metrics.items():
            writer.add_scalar(f"reference/{group}_{name}", value, 0)
    save_checkpoint(checkpoint_path)

print("==============================================")
print("Training: trainable base Actor, then causally gated spatiotemporal Attention")
print("Initialization model:", base_model)
print("History length:", history_len)
print("Attention model dim / heads:", model_dim, "/", num_heads)
print(
    "Initial gate / temperature / zero Attention delta head:",
    initial_gate,
    "/",
    gate_temperature,
    "/",
    True,
)
print("Fixed manifest groups: standard, dense")
print("Training datasets:", ", ".join(training_config["train_manifest_dataset_ids"]))
print(
    "Validation datasets:",
    ", ".join(training_config["validation_manifest_dataset_ids"]),
)
print(
    "Base Actor start / Attention start:",
    actor_start_step,
    "/",
    attention_start_step,
)
print(
    "LR warmup / decay / base fine-tune ratio / Attention base warmup:",
    actor_lr_warmup_steps,
    "/",
    actor_lr_decay_steps,
    "/",
    base_finetune_lr_ratio,
    "/",
    attention_base_warmup_steps,
)
print("Base Actor is frozen for the full Attention stage.")
print("Replay group ratios:", replay_group_ratios)
print("Critic reward scale:", reward_scale)
print(
    "Policy linear speed range:",
    0.0,
    "/",
    forward_speed,
)
print(
    "Slowdown distance / penalty:",
    slowdown_distance,
    "/",
    slowdown_penalty_weight,
)
print(
    "Risk-gate supervision / positive weight / safe sparsity:",
    gate_supervision_weight,
    "/",
    gate_positive_weight,
    "/",
    gate_safe_sparsity_weight,
)
print("Actor anchor / correction weight:", actor_anchor_weight, "/", attention_correction_weight)
print(
    "Robot safe distance / team progress / team completion:",
    robot_safe_distance,
    "/",
    team_progress_bonus,
    "/",
    team_completion_bonus,
)
print(
    "Risk label visible range / distance / TTC horizon:",
    interaction_risk_visible_range,
    "/",
    interaction_risk_distance,
    "/",
    interaction_risk_ttc_horizon,
)
print(
    "Hard-case sampling start / strength / uniform fraction / EMA:",
    hard_case_sampling_start_step,
    "/",
    hard_case_sampling_strength,
    "/",
    hard_case_uniform_fraction,
    "/",
    hard_case_score_ema,
)
print("TD3 discount:", discount)
print("Batch size / expected samples per group:", batch_size, "/", batch_size // 2)
print(
    "Fixed evaluation episodes: standard=%d, dense=%d, seed=%d"
    % (standard_eval_episodes, dense_eval_episodes, evaluation_seed)
)
print("Early stopping patience:", early_stopping_patience, "evaluations")
print("Fixed exploration noise:", exploration_noise)
print("Device:", agent.device)
print("Checkpoint:", checkpoint_path)
print("==============================================")

try:
    while episode < max_episodes:
        states = env.reset()
        case_name = env.current_scenario_id()
        case_group = env.current_scenario_group()
        if case_group not in replay_group_ratios:
            raise ValueError(f"Unsupported training group: {case_group}")
        initial_goal_distance = float(np.mean([state[20] for state in states]))
        histories = make_histories(states, history_len)
        active = [True] * env.num_agents
        episode_rewards = np.zeros(env.num_agents, dtype=np.float32)
        episode_success = np.zeros(env.num_agents, dtype=np.int32)
        episode_collision = np.zeros(env.num_agents, dtype=np.int32)
        last_losses = None

        for episode_step in range(max_episode_steps):
            interaction_risks = env.interaction_risk_labels(active)
            raw_actions = []
            env_actions = []
            current_histories = {}
            for index in range(env.num_agents):
                current_histories[index] = history_array(histories, index)
                if not active[index]:
                    raw_actions.append(np.zeros(2, dtype=np.float32))
                    env_actions.append([0.0, 0.0])
                    continue
                raw_action = agent.select_action(current_histories[index])
                raw_action = np.clip(
                    raw_action
                    + np.random.normal(0.0, exploration_noise, size=2),
                    -1.0,
                    1.0,
                ).astype(np.float32)
                raw_actions.append(raw_action)
                env_actions.append(policy_action_to_env(raw_action, forward_speed))

            next_states, rewards, dones, targets, collisions = env.step(
                env_actions, active
            )
            environment_steps += 1
            truncated = episode_step + 1 >= max_episode_steps
            for index, next_state in enumerate(next_states):
                histories[index].append(np.asarray(next_state, dtype=np.float32))
                if not active[index]:
                    continue
                next_history = history_array(histories, index)
                shaped_reward = rewards[index] + local_driving_shaping(
                    next_state,
                    env_actions[index],
                    slowdown_distance,
                    slowdown_penalty_weight,
                    forward_speed,
                )
                replay_buffer.add(
                    current_histories[index],
                    raw_actions[index],
                    shaped_reward,
                    dones[index] or truncated,
                    next_history,
                    case_group,
                    interaction_risk=max(
                        float(interaction_risks[index]), float(collisions[index])
                    ),
                )
                agent_samples += 1
                episode_rewards[index] += shaped_reward
                episode_success[index] = max(
                    episode_success[index], int(targets[index])
                )
                episode_collision[index] = max(
                    episode_collision[index], int(collisions[index])
                )
                if dones[index] or truncated:
                    active[index] = False

            if not base_stage_saved and agent_samples >= attention_start_step:
                torch.save(agent.actor.base_actor.state_dict(), base_stage_actor_path)
                base_stage_saved = True
                evaluations_without_improvement = 0
                agent.set_attention_enabled(True)
                print("Base stage completed. Saved Actor:", base_stage_actor_path)

            if len(replay_buffer) >= learning_starts:
                step_losses = agent.train_step(
                    replay_buffer,
                    batch_size=batch_size,
                    discount=discount,
                    actor_start_step=actor_start_step,
                    attention_start_step=attention_start_step,
                    actor_lr_warmup_steps=actor_lr_warmup_steps,
                    actor_lr_decay_steps=actor_lr_decay_steps,
                    actor_lr_min_ratio=actor_lr_min_ratio,
                    base_finetune_lr_ratio=base_finetune_lr_ratio,
                    attention_base_warmup_steps=attention_base_warmup_steps,
                    gate_supervision_weight=gate_supervision_weight,
                    gate_positive_weight=gate_positive_weight,
                    gate_safe_sparsity_weight=gate_safe_sparsity_weight,
                    actor_anchor_weight=actor_anchor_weight,
                    attention_correction_weight=attention_correction_weight,
                    reward_scale=reward_scale,
                    gradient_clip=gradient_clip,
                    environment_step=agent_samples,
                )
                if last_losses is None:
                    last_losses = {}
                last_losses.update(
                    {
                        name: value
                        for name, value in step_losses.items()
                        if value is not None
                    }
                )
            if not any(active):
                break

        episode += 1
        success_rate = float(episode_success.mean())
        collision_rate = float(episode_collision.mean())
        full_success = int(episode_success.sum() == env.num_agents)
        timeout = int(any(active))
        if agent_samples >= hard_case_sampling_start_step:
            failure_signal = episode_failure_signal(
                full_success, collision_rate, timeout
            )
            case_failure_scores[case_name] = update_failure_score(
                case_failure_scores.get(case_name, 0.0),
                failure_signal,
                ema=hard_case_score_ema,
            )
            apply_group_balanced_hard_case_weights(
                env.curriculum_cases,
                case_failure_scores,
                strength=hard_case_sampling_strength,
                uniform_fraction=hard_case_uniform_fraction,
            )
        writer.add_scalar("train/success_rate", success_rate, episode)
        writer.add_scalar("train/collision_rate", collision_rate, episode)
        writer.add_scalar("train/full_success", full_success, episode)
        writer.add_scalar("train/timeout", timeout, episode)
        writer.add_scalar("train/mean_reward", episode_rewards.mean(), episode)
        writer.add_scalar(
            "diagnostic/initial_goal_distance_mean", initial_goal_distance, episode
        )
        writer.add_scalar(
            f"diagnostic/{case_group}_initial_goal_distance_mean",
            initial_goal_distance,
            episode,
        )
        writer.add_scalar(
            "diagnostic/current_case_failure_score",
            case_failure_scores.get(case_name, 0.0),
            episode,
        )
        for group, count in replay_buffer.group_counts().items():
            writer.add_scalar(f"replay/{group}_count", count, episode)
        if last_losses:
            for name, value in last_losses.items():
                if value is not None:
                    namespace = (
                        "diagnostic"
                        if "_gate_" in name
                        or "attention_" in name
                        or "_correction_" in name
                        or "risk_" in name
                        or name.startswith("interaction_risk")
                        else "optimization"
                    )
                    writer.add_scalar(
                        f"{namespace}/{name}", value, agent.total_updates
                    )

        print(
            "Episode %d | phase=%s | group=%s | case=%s | samples=%d | steps=%d | "
            "success=%.3f | collision=%.3f | full=%d | replay=%d"
            % (
                episode,
                "attention" if agent.attention_enabled else "base",
                case_group,
                case_name,
                agent_samples,
                episode_step + 1,
                success_rate,
                collision_rate,
                full_success,
                len(replay_buffer),
            )
        )

        if episode % checkpoint_interval == 0:
            save_checkpoint(checkpoint_path)
        if episode % eval_interval != 0:
            continue

        standard_metrics = evaluate_group(
            agent,
            env,
            validation_cases,
            "standard",
            history_len,
            standard_eval_episodes,
            max_episode_steps,
            evaluation_seed,
            forward_speed,
        )
        dense_metrics = evaluate_group(
            agent,
            env,
            validation_cases,
            "dense",
            history_len,
            dense_eval_episodes,
            max_episode_steps,
            evaluation_seed + 1000,
            forward_speed,
        )
        print("Eval standard:", standard_metrics)
        print("Eval dense:", dense_metrics)
        for group, metrics in (
            ("standard", standard_metrics),
            ("dense", dense_metrics),
        ):
            for name, value in metrics.items():
                writer.add_scalar(f"eval/{group}_{name}", value, episode)

        if not agent.attention_enabled:
            print(
                "Base-stage evaluation recorded; best selection starts in "
                "Attention stage"
            )
            save_checkpoint(checkpoint_path)
            continue

        if attention_reference_metrics is None:
            print("Evaluating frozen base-stage branch for causal Attention reference")
            attention_reference_metrics = {
                "standard": evaluate_group(
                    agent,
                    env,
                    validation_cases,
                    "standard",
                    history_len,
                    standard_eval_episodes,
                    max_episode_steps,
                    evaluation_seed,
                    forward_speed,
                    attention_enabled=False,
                ),
                "dense": evaluate_group(
                    agent,
                    env,
                    validation_cases,
                    "dense",
                    history_len,
                    dense_eval_episodes,
                    max_episode_steps,
                    evaluation_seed + 1000,
                    forward_speed,
                    attention_enabled=False,
                ),
            }
            print(
                "Base-stage reference standard:",
                attention_reference_metrics["standard"],
            )
            print(
                "Base-stage reference dense:", attention_reference_metrics["dense"])
            for group, metrics in attention_reference_metrics.items():
                for name, value in metrics.items():
                    writer.add_scalar(
                        f"reference/base_stage_{group}_{name}", value, episode
                    )
            save_checkpoint(checkpoint_path)

        candidate = {"standard": standard_metrics, "dense": dense_metrics}
        candidate_key = best_key(standard_metrics, dense_metrics)
        reference_key = best_key(
            reference_metrics["standard"], reference_metrics["dense"]
        )
        attention_reference_key = best_key(
            attention_reference_metrics["standard"],
            attention_reference_metrics["dense"],
        )
        incumbent_key = (
            None
            if best_metrics is None
            else best_key(best_metrics["standard"], best_metrics["dense"])
        )
        if (
            candidate_key > reference_key
            and candidate_key > attention_reference_key
            and (incumbent_key is None or candidate_key > incumbent_key)
        ):
            best_metrics = candidate
            evaluations_without_improvement = 0
            torch.save(agent.actor.state_dict(), f"pytorch_models/{model_name}_actor.pth")
            save_checkpoint(best_checkpoint_path)
            print("Updated causal Attention best:", best_checkpoint_path)
        else:
            evaluations_without_improvement += 1
            if candidate_key <= reference_key:
                print("Attention candidate did not exceed the immutable 5D reference")
            if candidate_key <= attention_reference_key:
                print("Attention candidate did not exceed the frozen base-stage branch")
        save_checkpoint(checkpoint_path)
        if (
            early_stopping_patience > 0
            and evaluations_without_improvement >= early_stopping_patience
        ):
            print(
                "Early stopping after %d evaluations without dual-benchmark improvement"
                % evaluations_without_improvement
            )
            break
finally:
    save_checkpoint(checkpoint_path)
    writer.close()
