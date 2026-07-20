#!/usr/bin/env python3
"""Evaluate Attention ablations on the frozen multi-robot validation manifests."""

import json
import os
import random
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

from multi_agent_velodyne_env import MultiAgentGazeboEnv
from scenario_manifests import load_manifest_cases
from spatiotemporal_attention import BaseActor, SpatioTemporalTD3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TD3_ROOT = PROJECT_ROOT / "TD3"
AGENT_NAMES = [f"r{index}" for index in range(1, 6)]


def env_float(name, default):
    value = os.environ.get(name)
    return default if value is None or not value.strip() else float(value)


def env_int(name, default):
    value = os.environ.get(name)
    return default if value is None or not value.strip() else int(value)


def resolve_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else (TD3_ROOT / path).resolve()


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


def summarize(values):
    if not values:
        return None
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "std": float(array.std()),
        "min": float(array.min()),
        "max": float(array.max()),
        "count": int(array.size),
    }


class BasePolicy:
    def __init__(self, state_dict, device):
        self.device = device
        self.actor = BaseActor().to(device)
        self.actor.load_state_dict(state_dict)
        self.actor.eval()

    def reset_diagnostics(self):
        return None

    def select_action(self, history, interaction_risk=None):
        state = torch.as_tensor(
            history[-1], dtype=torch.float32, device=self.device
        ).unsqueeze(0)
        with torch.no_grad():
            action = self.actor(state)
        return action.cpu().numpy().reshape(-1)

    def diagnostics(self):
        return {}


class AttentionPolicy:
    """Evaluate the trained Actor with its base branch or Attention ablations."""

    def __init__(self, agent, mode, fixed_gate=None):
        if mode not in {"base", "fixed", "learned"}:
            raise ValueError(f"Unsupported Attention evaluation mode: {mode}")
        if mode == "fixed" and not 0.0 <= fixed_gate <= 1.0:
            raise ValueError("Fixed gate must be between 0 and 1")
        self.agent = agent
        self.mode = mode
        self.fixed_gate = fixed_gate
        self.reset_diagnostics()

    def reset_diagnostics(self):
        self.gates = []
        self.interaction_risks = []
        self.attention_delta_linear = []
        self.attention_delta_angular = []
        self.applied_delta_linear = []
        self.applied_delta_angular = []

    def select_action(self, history, interaction_risk=None):
        history_tensor = torch.as_tensor(
            history, dtype=torch.float32, device=self.agent.device
        ).unsqueeze(0)
        self.agent.actor.eval()
        with torch.no_grad():
            (
                learned_action,
                base_action,
                attention_action,
                learned_gate,
                _,
            ) = self.agent.actor(
                history_tensor, attention_enabled=True, return_details=True
            )
            if self.mode == "base":
                action = base_action
            elif self.mode == "fixed":
                action = torch.lerp(base_action, attention_action, self.fixed_gate)
            else:
                action = learned_action

        base = base_action.cpu().numpy().reshape(-1)
        attention = attention_action.cpu().numpy().reshape(-1)
        selected = action.cpu().numpy().reshape(-1)
        self.gates.append(float(learned_gate.item()))
        self.interaction_risks.append(
            None if interaction_risk is None else float(interaction_risk)
        )
        self.attention_delta_linear.append(float(attention[0] - base[0]))
        self.attention_delta_angular.append(float(attention[1] - base[1]))
        self.applied_delta_linear.append(float(selected[0] - base[0]))
        self.applied_delta_angular.append(float(selected[1] - base[1]))
        return selected

    def diagnostics(self):
        paired_risks = [
            risk for risk in self.interaction_risks if risk is not None
        ]
        paired_gates = [
            gate
            for gate, risk in zip(self.gates, self.interaction_risks)
            if risk is not None
        ]
        risk_gate_metrics = {}
        if paired_risks:
            risks = np.asarray(paired_risks, dtype=np.float64)
            gates = np.asarray(paired_gates, dtype=np.float64)
            low_risk = risks < 0.1
            high_risk = risks >= 0.5
            risk_gate_metrics = {
                "interaction_risk": summarize(paired_risks),
                "gate_mean_low_risk": (
                    float(gates[low_risk].mean()) if np.any(low_risk) else None
                ),
                "gate_mean_high_risk": (
                    float(gates[high_risk].mean()) if np.any(high_risk) else None
                ),
                "gate_risk_correlation": (
                    float(np.corrcoef(gates, risks)[0, 1])
                    if len(gates) > 1
                    and gates.std() > 1e-8
                    and risks.std() > 1e-8
                    else None
                ),
            }
        return {
            "learned_gate": summarize(self.gates),
            "attention_delta_linear": summarize(self.attention_delta_linear),
            "attention_delta_angular": summarize(self.attention_delta_angular),
            "applied_delta_linear": summarize(self.applied_delta_linear),
            "applied_delta_angular": summarize(self.applied_delta_angular),
            **risk_gate_metrics,
        }


def evaluate_group(
    policy_name,
    policy,
    env,
    evaluation_cases,
    group,
    history_len,
    episodes,
    max_episode_steps,
    evaluation_seed,
    forward_speed,
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
    group_cases = [case for case in evaluation_cases if case["group"] == group]
    if not group_cases:
        raise ValueError(f"No validation manifest cases found for group: {group}")

    successes = 0
    collisions = 0
    full_successes = 0
    timeouts = 0
    initial_goal_distances = []
    policy.reset_diagnostics()
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

        for episode in range(episodes):
            states = env.reset()
            scenario_id = env.current_scenario_id()
            initial_goal_distances.extend(float(state[20]) for state in states)
            histories = make_histories(states, history_len)
            active = [True] * env.num_agents
            episode_success = np.zeros(env.num_agents, dtype=np.int32)
            episode_collision = np.zeros(env.num_agents, dtype=np.int32)
            for _ in range(max_episode_steps):
                interaction_risks = env.interaction_risk_labels(active)
                actions = []
                for index in range(env.num_agents):
                    if not active[index]:
                        actions.append([0.0, 0.0])
                        continue
                    raw_action = policy.select_action(
                        history_array(histories, index),
                        interaction_risk=interaction_risks[index],
                    )
                    actions.append(policy_action_to_env(raw_action, forward_speed))
                next_states, _, dones, targets, collision_flags = env.step(actions, active)
                for index, next_state in enumerate(next_states):
                    histories[index].append(np.asarray(next_state, dtype=np.float32))
                    if not active[index]:
                        continue
                    episode_success[index] = max(episode_success[index], int(targets[index]))
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
                "Eval | policy=%s | group=%s | episode=%d/%d | scenario=%s | "
                "success=%d/%d | collision=%d/%d | full=%d"
                % (
                    policy_name,
                    group,
                    episode + 1,
                    episodes,
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

    total_agents = episodes * env.num_agents
    return {
        "success_rate": successes / total_agents,
        "collision_rate": collisions / total_agents,
        "full_success_rate": full_successes / episodes,
        "timeout_rate": timeouts / episodes,
        "initial_goal_distance_mean": float(np.mean(initial_goal_distances)),
        "action_diagnostics": policy.diagnostics(),
    }


def make_attention_agent(checkpoint, base_actor_state):
    config = checkpoint["config"]
    agent = SpatioTemporalTD3(
        base_actor_state,
        history_len=int(config["history_len"]),
        model_dim=int(config["model_dim"]),
        num_heads=int(config["num_heads"]),
        attention_logit_scale=float(config["attention_logit_scale"]),
        initial_gate=float(config["initial_gate"]),
        gate_temperature=float(config.get("gate_temperature", 1.0)),
        base_actor_lr=float(config["base_actor_lr"]),
        attention_lr=float(config["attention_lr"]),
        critic_lr=float(config["critic_lr"]),
        critic_hidden_dim=int(config["critic_hidden_dim"]),
    )
    agent.load_state_dict(checkpoint["agent"])
    agent.actor.eval()
    return agent


def main():
    checkpoint_path = resolve_path(
        os.environ.get(
            "DRL_ATTENTION_EVAL_CHECKPOINT",
            "checkpoints/TD3_velodyne_multi_fixed_manifest_attention_best.pt",
        )
    )
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Attention checkpoint does not exist: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    base_model = config["base_model"]
    reference_actor_path = TD3_ROOT / "pytorch_models" / f"{base_model}_actor.pth"
    base_stage_path = resolve_path(
        os.environ.get(
            "DRL_ATTENTION_EVAL_BASE_STAGE_ACTOR",
            "pytorch_models/TD3_velodyne_multi_fixed_manifest_attention_base_stage_actor.pth",
        )
    )
    if not reference_actor_path.is_file() or not base_stage_path.is_file():
        raise FileNotFoundError("The immutable 5D Actor or base-stage Actor is missing")
    reference_state = torch.load(reference_actor_path, map_location="cpu", weights_only=True)
    base_stage_state = torch.load(base_stage_path, map_location="cpu", weights_only=True)
    attention_agent = make_attention_agent(checkpoint, reference_state)

    manifest_root = PROJECT_ROOT / "fixed_scenarios_v1" / "data" / "fixed_v1"
    default_validation_manifests = os.pathsep.join(
        [
            str(manifest_root / "standard" / "validation.json.gz"),
            str(manifest_root / "dense" / "validation.json.gz"),
        ]
    )
    validation_manifest_paths = os.environ.get(
        "DRL_ATTENTION_VALIDATION_MANIFEST_PATHS", default_validation_manifests
    ).strip()
    os.environ["DRL_MULTI_MANIFEST_PATHS"] = validation_manifest_paths
    os.environ["DRL_MULTI_MANIFEST_SAMPLING"] = "cycle"
    validation_cases, metadata = load_manifest_cases(
        validation_manifest_paths, AGENT_NAMES
    )
    if {item["split"] for item in metadata} != {"validation"}:
        raise ValueError("Attention evaluation requires validation manifests only")

    episodes = env_int(
        "DRL_ATTENTION_EVAL_EPISODES", int(config["standard_eval_episodes"])
    )
    if episodes <= 0:
        raise ValueError("DRL_ATTENTION_EVAL_EPISODES must be positive")
    fixed_gate = env_float("DRL_ATTENTION_EVAL_FIXED_GATE", 1.0)
    if not 0.0 <= fixed_gate <= 1.0:
        raise ValueError("DRL_ATTENTION_EVAL_FIXED_GATE must be between 0 and 1")
    history_len = int(config["history_len"])
    max_episode_steps = int(config["max_episode_steps"])
    evaluation_seed = int(config["evaluation_seed"])
    forward_speed = float(config["forward_speed"])
    launchfile = os.environ.get(
        "DRL_ATTENTION_LAUNCHFILE", "multi_robot_scenario_attention_5.launch"
    )

    policies = {
        "frozen_5d": BasePolicy(reference_state, device),
        "base_stage": BasePolicy(base_stage_state, device),
        "final_base_branch": AttentionPolicy(attention_agent, "base"),
        "fixed_gate": AttentionPolicy(attention_agent, "fixed", fixed_gate),
        "learned_gate": AttentionPolicy(attention_agent, "learned"),
    }
    env = MultiAgentGazeboEnv(
        launchfile,
        20,
        agent_names=AGENT_NAMES,
        cooperative_reward=False,
        anti_stagnation_reward=False,
        wall_clearance_reward=False,
        local_navigation_reward=False,
        robot_safe_distance=0.0,
        weak_coupling_layout=True,
        scenario_mode="manifest",
        active_neighbors_only=True,
    )
    startup_timeout = env_float("DRL_ATTENTION_STARTUP_ODOM_TIMEOUT", 240.0)
    for agent_name in AGENT_NAMES:
        env.wait_for_odom(agent_name, timeout=startup_timeout)

    results = {
        "evaluation_version": "attention_ablation_v1",
        "checkpoint": str(checkpoint_path),
        "checkpoint_agent_samples": int(checkpoint["agent_samples"]),
        "validation_datasets": [item["dataset_id"] for item in metadata],
        "episodes_per_group": episodes,
        "evaluation_seed": evaluation_seed,
        "fixed_gate": fixed_gate,
        "policies": {},
    }
    for policy_name, policy in policies.items():
        print("=" * 72)
        print("Evaluating policy:", policy_name)
        results["policies"][policy_name] = {
            "standard": evaluate_group(
                policy_name,
                policy,
                env,
                validation_cases,
                "standard",
                history_len,
                episodes,
                max_episode_steps,
                evaluation_seed,
                forward_speed,
            ),
            "dense": evaluate_group(
                policy_name,
                policy,
                env,
                validation_cases,
                "dense",
                history_len,
                episodes,
                max_episode_steps,
                evaluation_seed + 1000,
                forward_speed,
            ),
        }
        print(json.dumps(results["policies"][policy_name], ensure_ascii=True))

    output_value = os.environ.get("DRL_ATTENTION_EVAL_RESULTS_PATH", "").strip()
    output_path = (
        resolve_path(output_value)
        if output_value
        else TD3_ROOT
        / "results"
        / f"attention_ablation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("Attention ablation results:", output_path)


if __name__ == "__main__":
    main()
