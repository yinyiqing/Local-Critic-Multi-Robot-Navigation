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
from sequence_replay_buffer import SequenceReplayBuffer
from spatiotemporal_attention import SpatioTemporalTD3


def env_int(name, default):
    value = os.environ.get(name)
    return default if value is None or not value.strip() else int(value)


def env_float(name, default):
    value = os.environ.get(name)
    return default if value is None or not value.strip() else float(value)


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


def evaluate_group(
    agent,
    env,
    group,
    history_len,
    episodes_per_case,
    max_episode_steps,
    evaluation_seed,
):
    original_cases = env.curriculum_cases
    original_index = env.curriculum_case_index
    original_case = env.current_curriculum_case
    original_sampling = os.environ.get("DRL_MULTI_CURRICULUM_SAMPLING")
    original_upper = env.upper
    original_lower = env.lower
    random_state = random.getstate()
    numpy_state = np.random.get_state()
    torch_state = torch.get_rng_state()
    cuda_states = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
    group_cases = [case for case in original_cases if case.get("group") == group]
    if not group_cases:
        raise ValueError(f"No curriculum cases found for evaluation group: {group}")

    episodes = int(episodes_per_case) * len(group_cases)
    successes = 0
    collisions = 0
    full_successes = 0
    timeouts = 0
    total_agents = episodes * env.num_agents
    try:
        env.curriculum_cases = group_cases
        env.curriculum_case_index = 0
        os.environ["DRL_MULTI_CURRICULUM_SAMPLING"] = "cycle"
        env.upper = 10.0
        env.lower = -10.0
        random.seed(evaluation_seed)
        np.random.seed(evaluation_seed)
        torch.manual_seed(evaluation_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(evaluation_seed)
        for _ in range(episodes):
            states = env.reset()
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
                    raw_action = agent.select_action(history_array(histories, index))
                    actions.append([(raw_action[0] + 1.0) / 2.0, raw_action[1]])
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
    finally:
        env.curriculum_cases = original_cases
        env.curriculum_case_index = original_index
        env.current_curriculum_case = original_case
        env.upper = original_upper
        env.lower = original_lower
        if original_sampling is None:
            os.environ.pop("DRL_MULTI_CURRICULUM_SAMPLING", None)
        else:
            os.environ["DRL_MULTI_CURRICULUM_SAMPLING"] = original_sampling
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
max_residual = env_float("DRL_ATTENTION_MAX_RESIDUAL", 0.25)
actor_lr = env_float("DRL_ATTENTION_ACTOR_LR", 1e-5)
critic_lr = env_float("DRL_ATTENTION_CRITIC_LR", 2e-5)
actor_start_step = env_int("DRL_ATTENTION_ACTOR_START_STEP", 5000)
actor_lr_warmup_steps = env_int("DRL_ATTENTION_ACTOR_WARMUP_STEPS", 10000)
actor_lr_decay_steps = env_int("DRL_ATTENTION_ACTOR_DECAY_STEPS", 100000)
actor_lr_min_ratio = env_float("DRL_ATTENTION_ACTOR_MIN_LR_RATIO", 0.1)
exploration_noise = env_float("DRL_ATTENTION_EXPLORATION_NOISE", 0.01)
gradient_clip = env_float("DRL_ATTENTION_GRADIENT_CLIP", 1.0)
reward_scale = env_float("DRL_ATTENTION_REWARD_SCALE", 0.1)
gate_penalty_weight = env_float("DRL_ATTENTION_GATE_PENALTY", 0.1)
residual_penalty_weight = env_float("DRL_ATTENTION_RESIDUAL_PENALTY", 0.05)
standard_residual_penalty_weight = env_float(
    "DRL_ATTENTION_STANDARD_RESIDUAL_PENALTY", 1.0
)
batch_size = env_int("DRL_ATTENTION_BATCH_SIZE", 64)
replay_capacity = env_int("DRL_ATTENTION_REPLAY_CAPACITY", 200000)
replay_group_ratios = {
    "standard": env_float("DRL_ATTENTION_REPLAY_STANDARD_RATIO", 1.0),
    "pair": env_float("DRL_ATTENTION_REPLAY_PAIR_RATIO", 1.0),
    "three": env_float("DRL_ATTENTION_REPLAY_THREE_RATIO", 1.0),
}
learning_starts = env_int("DRL_ATTENTION_LEARNING_STARTS", 2000)
max_episodes = env_int("DRL_ATTENTION_MAX_EPISODES", 1000)
max_episode_steps = env_int("DRL_ATTENTION_MAX_EPISODE_STEPS", 300)
eval_interval = env_int("DRL_ATTENTION_EVAL_INTERVAL", 25)
eval_episodes_per_case = env_int("DRL_ATTENTION_EVAL_EPISODES_PER_CASE", 4)
standard_eval_episodes = env_int("DRL_ATTENTION_STANDARD_EVAL_EPISODES", 12)
evaluation_seed = env_int("DRL_ATTENTION_EVAL_SEED", 20260713)
early_stopping_patience = env_int("DRL_ATTENTION_EARLY_STOPPING_PATIENCE", 8)
checkpoint_interval = env_int("DRL_ATTENTION_CHECKPOINT_INTERVAL", 10)

agent_names = [f"r{index}" for index in range(1, 6)]
launchfile = os.environ.get(
    "DRL_ATTENTION_LAUNCHFILE", "multi_robot_scenario_attention_5.launch"
)
base_model = os.environ.get(
    "DRL_ATTENTION_BASE_MODEL",
    "TD3_velodyne_multi_v4_curriculum_stage2_to_5d_geo_critic_from_5a_guarded_best",
)
model_name = os.environ.get(
    "DRL_ATTENTION_MODEL_NAME",
    "TD3_velodyne_multi_v5_attention_residual_from_5d_balanced_v2",
)
base_actor_path = os.path.join("pytorch_models", f"{base_model}_actor.pth")
checkpoint_path = os.path.join("checkpoints", f"{model_name}_latest.pt")
best_checkpoint_path = os.path.join("checkpoints", f"{model_name}_best.pt")

random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

base_actor_state = torch.load(base_actor_path, map_location="cpu", weights_only=True)
agent = SpatioTemporalTD3(
    base_actor_state,
    history_len=history_len,
    model_dim=model_dim,
    num_heads=num_heads,
    max_residual=max_residual,
    actor_lr=actor_lr,
    critic_lr=critic_lr,
)
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
    robot_safe_distance=0.0,
    weak_coupling_layout=True,
    scenario_mode="curriculum",
    active_neighbors_only=True,
)
time.sleep(5)

timestamp = datetime.now().strftime("%b%d_%H-%M-%S")
writer = SummaryWriter(
    log_dir=os.path.join("runs", f"attention_{timestamp}_{socket.gethostname()}")
)
episode = 0
environment_steps = 0
agent_samples = 0
best_metrics = None
evaluations_without_improvement = 0


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
            "config": {
                "training_version": 2,
                "history_len": history_len,
                "model_dim": model_dim,
                "num_heads": num_heads,
                "max_residual": max_residual,
                "base_model": base_model,
                "reward_scale": reward_scale,
                "replay_group_ratios": replay_group_ratios,
            },
        },
        path,
    )


if os.path.exists(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    expected = (
        2,
        history_len,
        model_dim,
        num_heads,
        max_residual,
        base_model,
        reward_scale,
        replay_group_ratios,
    )
    restored = (
        config.get("training_version"),
        config["history_len"],
        config["model_dim"],
        config["num_heads"],
        config["max_residual"],
        config["base_model"],
        config.get("reward_scale"),
        config.get("replay_group_ratios"),
    )
    if restored != expected:
        raise ValueError(f"Checkpoint config mismatch: {restored} != {expected}")
    agent.load_state_dict(checkpoint["agent"])
    replay_buffer.load_state_dict(checkpoint["replay_buffer"])
    episode = int(checkpoint["episode"])
    environment_steps = int(checkpoint["environment_steps"])
    agent_samples = int(checkpoint["agent_samples"])
    best_metrics = checkpoint.get("best_metrics")
    evaluations_without_improvement = int(
        checkpoint.get("evaluations_without_improvement", 0)
    )
    print("Resumed attention training from:", checkpoint_path)

print("==============================================")
print("Training: 5D frozen actor + spatiotemporal attention residual")
print("Base model:", base_model)
print("History length:", history_len)
print("Attention model dim / heads:", model_dim, "/", num_heads)
print("Mixed curriculum groups: standard, pair, three")
print("Reward: base individual reward only")
print(
    "Actor start / LR warmup / decay:",
    actor_start_step,
    "/",
    actor_lr_warmup_steps,
    "/",
    actor_lr_decay_steps,
)
print("Replay group ratios:", replay_group_ratios)
print("Critic reward scale:", reward_scale)
print(
    "Gate / residual / standard residual penalties:",
    gate_penalty_weight,
    "/",
    residual_penalty_weight,
    "/",
    standard_residual_penalty_weight,
)
print(
    "Fixed evaluation: standard=%d, dense=%d per case, seed=%d"
    % (standard_eval_episodes, eval_episodes_per_case, evaluation_seed)
)
print("Early stopping patience:", early_stopping_patience, "evaluations")
print("Fixed exploration noise:", exploration_noise)
print("Device:", agent.device)
print("Checkpoint:", checkpoint_path)
print("==============================================")

try:
    while episode < max_episodes:
        states = env.reset()
        case_name = str(env.current_curriculum_case.get("name", "unknown"))
        case_group = str(env.current_curriculum_case.get("group", "unknown"))
        histories = make_histories(states, history_len)
        active = [True] * env.num_agents
        episode_rewards = np.zeros(env.num_agents, dtype=np.float32)
        episode_success = np.zeros(env.num_agents, dtype=np.int32)
        episode_collision = np.zeros(env.num_agents, dtype=np.int32)
        last_losses = None

        for episode_step in range(max_episode_steps):
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
                env_actions.append([(raw_action[0] + 1.0) / 2.0, raw_action[1]])

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
                replay_buffer.add(
                    current_histories[index],
                    raw_actions[index],
                    rewards[index],
                    dones[index] or truncated,
                    next_history,
                    case_group,
                )
                agent_samples += 1
                episode_rewards[index] += rewards[index]
                episode_success[index] = max(
                    episode_success[index], int(targets[index])
                )
                episode_collision[index] = max(
                    episode_collision[index], int(collisions[index])
                )
                if dones[index] or truncated:
                    active[index] = False

            if len(replay_buffer) >= learning_starts:
                step_losses = agent.train_step(
                    replay_buffer,
                    batch_size=batch_size,
                    actor_start_step=actor_start_step,
                    actor_lr_warmup_steps=actor_lr_warmup_steps,
                    actor_lr_decay_steps=actor_lr_decay_steps,
                    actor_lr_min_ratio=actor_lr_min_ratio,
                    reward_scale=reward_scale,
                    gate_penalty_weight=gate_penalty_weight,
                    residual_penalty_weight=residual_penalty_weight,
                    standard_residual_penalty_weight=(
                        standard_residual_penalty_weight
                    ),
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
        writer.add_scalar("train/success_rate", success_rate, episode)
        writer.add_scalar("train/collision_rate", collision_rate, episode)
        writer.add_scalar("train/full_success", full_success, episode)
        writer.add_scalar("train/mean_reward", episode_rewards.mean(), episode)
        for group, count in replay_buffer.group_counts().items():
            writer.add_scalar(f"replay/{group}_count", count, episode)
        if last_losses:
            for name, value in last_losses.items():
                if value is not None:
                    namespace = (
                        "diagnostic"
                        if "_gate_" in name or "_residual_" in name
                        else "optimization"
                    )
                    writer.add_scalar(
                        f"{namespace}/{name}", value, agent.total_updates
                    )

        print(
            "Episode %d | group=%s | case=%s | samples=%d | steps=%d | "
            "success=%.3f | collision=%.3f | full=%d | replay=%d"
            % (
                episode,
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
            "standard",
            history_len,
            standard_eval_episodes,
            max_episode_steps,
            evaluation_seed,
        )
        dense_metrics = evaluate_group(
            agent,
            env,
            "three",
            history_len,
            eval_episodes_per_case,
            max_episode_steps,
            evaluation_seed + 1000,
        )
        print("Eval standard:", standard_metrics)
        print("Eval three:", dense_metrics)
        for group, metrics in (("standard", standard_metrics), ("three", dense_metrics)):
            for name, value in metrics.items():
                writer.add_scalar(f"eval/{group}_{name}", value, episode)

        candidate = {"standard": standard_metrics, "three": dense_metrics}
        if best_metrics is None or best_key(standard_metrics, dense_metrics) > best_key(
            best_metrics["standard"], best_metrics["three"]
        ):
            best_metrics = candidate
            evaluations_without_improvement = 0
            torch.save(agent.actor.state_dict(), f"pytorch_models/{model_name}_actor.pth")
            save_checkpoint(best_checkpoint_path)
            print("Updated dual-benchmark best:", best_checkpoint_path)
        else:
            evaluations_without_improvement += 1
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
