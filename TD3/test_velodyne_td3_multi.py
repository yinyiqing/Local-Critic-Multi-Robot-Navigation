import json
import os
import random
import socket
import time
from collections import deque
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.tensorboard import SummaryWriter

from multi_agent_velodyne_env import MultiAgentGazeboEnv


class Actor(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(Actor, self).__init__()

        self.layer_1 = nn.Linear(state_dim, 800)
        self.layer_2 = nn.Linear(800, 600)
        self.layer_3 = nn.Linear(600, action_dim)
        self.tanh = nn.Tanh()

    def forward(self, s):
        s = F.relu(self.layer_1(s))
        s = F.relu(self.layer_2(s))
        a = self.tanh(self.layer_3(s))
        return a


class TD3(object):
    def __init__(self, state_dim, action_dim):
        self.actor = Actor(state_dim, action_dim).to(device)

    def get_action(self, state):
        state = torch.Tensor(state.reshape(1, -1)).to(device)
        return self.actor(state).cpu().data.numpy().flatten()

    def load(self, filename, directory):
        self.actor.load_state_dict(
            torch.load("%s/%s_actor.pth" % (directory, filename), map_location=device)
        )


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def env_int(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def make_agent_names():
    explicit_names = os.environ.get("DRL_MULTI_AGENT_NAMES")
    if explicit_names and explicit_names.strip():
        names = [name.strip() for name in explicit_names.split(",") if name.strip()]
        if not names:
            raise ValueError("DRL_MULTI_AGENT_NAMES did not contain valid agent names")
        return names

    num_agents = env_int("DRL_MULTI_NUM_AGENTS", 2)
    if num_agents < 1 or num_agents > 10:
        raise ValueError("DRL_MULTI_NUM_AGENTS must be between 1 and 10")
    return [f"r{idx}" for idx in range(1, num_agents + 1)]


seed = env_int("DRL_MULTI_SEED", 0)
max_ep = 300
target_test_episodes = int(os.environ.get("DRL_MULTI_TEST_TARGET_EPISODES", "0"))
scenario_mode = os.environ.get("DRL_MULTI_SCENARIO", "standard").strip().lower()
base_file_name = "TD3_velodyne_multi_v4"
file_name = os.environ.get("DRL_MULTI_TEST_FILE_NAME", base_file_name)
launchfile = os.environ.get(
    "DRL_MULTI_TEST_LAUNCHFILE", "multi_robot_scenario_multi_2.launch"
)
resume_testing = True
default_state_path = (
    "./checkpoints/TD3_velodyne_multi_test_state.pt"
    if file_name == base_file_name
    else f"./checkpoints/{file_name}_test_state.pt"
)
default_test_stats_path = (
    "./results/TD3_velodyne_multi_test.npy"
    if file_name == base_file_name
    else f"./results/{file_name}_test.npy"
)
state_path = os.environ.get(
    "DRL_MULTI_TEST_STATE_PATH",
    default_state_path,
)
test_stats_path = os.environ.get(
    "DRL_MULTI_TEST_STATS_PATH",
    default_test_stats_path,
)
trace_failures = env_flag("DRL_MULTI_TRACE_FAILURES", False)
trace_failure_mode = os.environ.get("DRL_MULTI_TRACE_FAILURE_MODE", "timeout").strip().lower()
trace_window_steps = max(env_int("DRL_MULTI_TRACE_WINDOW_STEPS", 100), 1)
trace_dir = os.environ.get(
    "DRL_MULTI_TRACE_DIR",
    os.path.join("./results", f"{file_name}_failure_traces"),
)
print_every_episodes = 10
environment_dim = 20
robot_dim = 4
agent_names = make_agent_names()


def make_test_run_dir():
    timestamp = datetime.now().strftime("%b%d_%H-%M-%S")
    return os.path.join("runs", f"test_{file_name}_{timestamp}_{socket.gethostname()}")


def load_test_state():
    if not (resume_testing and os.path.exists(state_path)):
        return None
    return torch.load(state_path, map_location="cpu")


def save_test_state(payload):
    os.makedirs("./checkpoints", exist_ok=True)
    torch.save(payload, state_path)


def append_stats(record):
    os.makedirs("./results", exist_ok=True)
    if os.path.exists(test_stats_path):
        history = list(np.load(test_stats_path, allow_pickle=True))
    else:
        history = []
    history.append(record)
    np.save(test_stats_path, np.array(history, dtype=object))


def current_case_name(env):
    case = getattr(env, "current_curriculum_case", None)
    if isinstance(case, dict):
        return str(case.get("name") or "unnamed_curriculum_case")
    return "standard"


def new_case_record():
    return {
        "episodes": 0,
        "success": 0,
        "collision": 0,
        "unresolved": 0,
        "full_success": 0,
        "timeout": 0,
        "env_steps": 0,
        "final_distance_sum": 0.0,
    }


def update_case_stats(
    case_stats,
    case_name,
    episode_success_count,
    episode_collision_count,
    episode_unresolved_count,
    full_success,
    timeout_episode,
    episode_env_steps,
    mean_final_distance,
):
    stats = case_stats.setdefault(case_name, new_case_record())
    stats["episodes"] += 1
    stats["success"] += int(episode_success_count)
    stats["collision"] += int(episode_collision_count)
    stats["unresolved"] += int(episode_unresolved_count)
    stats["full_success"] += int(full_success)
    stats["timeout"] += int(timeout_episode)
    stats["env_steps"] += int(episode_env_steps)
    stats["final_distance_sum"] += float(mean_final_distance)


def print_case_stats(case_stats):
    if not case_stats:
        return
    print("Case summary:")
    for name in sorted(case_stats):
        stats = case_stats[name]
        episodes = max(int(stats["episodes"]), 1)
        denom = episodes * len(agent_names)
        avg_steps = stats["env_steps"] / episodes
        avg_final_distance = stats["final_distance_sum"] / episodes
        print(
            "  %s | episodes=%i | success_rate=%.3f | collision_rate=%.3f | "
            "unresolved_rate=%.3f | full_success_rate=%.3f | timeout_rate=%.3f | "
            "avg_env_steps=%.1f | avg_final_distance=%.3f"
            % (
                name,
                stats["episodes"],
                stats["success"] / denom,
                stats["collision"] / denom,
                stats["unresolved"] / denom,
                stats["full_success"] / episodes,
                stats["timeout"] / episodes,
                avg_steps,
                avg_final_distance,
            )
        )


def scalar_or_none(value):
    if value is None:
        return None
    return float(value)


def should_trace_episode(timeout_episode, full_success, episode_unresolved_count):
    if not trace_failures:
        return False
    if trace_failure_mode == "all":
        return True
    if trace_failure_mode == "non_full_success":
        return not bool(full_success)
    if trace_failure_mode == "unresolved":
        return bool(episode_unresolved_count)
    return bool(timeout_episode)


def build_trace_step(step_idx, env_actions, active_mask, next_states, rewards, step_agents):
    agents = {}
    for idx, name in enumerate(agent_names):
        state = next_states[idx]
        info = step_agents[name]
        agents[name] = {
            "active": bool(active_mask[idx]),
            "action_linear": float(env_actions[idx][0]),
            "action_angular": float(env_actions[idx][1]),
            "reward": float(rewards[idx]),
            "target": bool(info["target"]),
            "collision": bool(info["collision"]),
            "distance": scalar_or_none(info["distance"]),
            "state_distance": float(state[-4]),
            "theta": float(state[-3]),
            "progress": float(info["progress"]),
            "min_laser": scalar_or_none(info["min_laser"]),
            "nearest_robot_distance": scalar_or_none(
                info["nearest_robot_distance"]
            ),
        }
    return {"step": int(step_idx), "agents": agents}


def write_failure_trace(
    episode_num,
    episode_env_steps,
    episode_agent_samples,
    mean_reward,
    episode_success_flags,
    episode_collision_flags,
    episode_final_distances,
    episode_unresolved_count,
    full_success,
    timeout_episode,
    trace_steps,
):
    os.makedirs(trace_dir, exist_ok=True)
    reason = "timeout" if timeout_episode else "failure"
    output_path = os.path.join(trace_dir, f"episode_{episode_num:04d}_{reason}.json")
    agent_summaries = {}
    for idx, name in enumerate(agent_names):
        agent_summaries[name] = {
            "success": int(episode_success_flags[idx]),
            "collision": int(episode_collision_flags[idx]),
            "final_distance": scalar_or_none(episode_final_distances[name]),
        }
    payload = {
        "episode_num": int(episode_num),
        "trace_window_steps": int(trace_window_steps),
        "trace_failure_mode": trace_failure_mode,
        "summary": {
            "episode_env_steps": int(episode_env_steps),
            "episode_agent_samples": int(episode_agent_samples),
            "mean_reward": float(mean_reward),
            "success_count": int(np.sum(episode_success_flags)),
            "collision_count": int(np.sum(episode_collision_flags)),
            "unresolved_count": int(episode_unresolved_count),
            "full_success": int(full_success),
            "timeout": int(timeout_episode),
        },
        "agents": agent_summaries,
        "steps": list(trace_steps),
    }
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    summary_path = os.path.join(trace_dir, "summary.jsonl")
    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload["summary"], sort_keys=True) + "\n")
    print("Failure trace saved:", output_path)


env = MultiAgentGazeboEnv(
    launchfile,
    environment_dim,
    agent_names=agent_names,
    cooperative_reward=False,
    robot_safe_distance=0.0,
    weak_coupling_layout=True,
    scenario_mode=scenario_mode,
)
time.sleep(5)
random.seed(seed)
torch.manual_seed(seed)
np.random.seed(seed)
state_dim = environment_dim + robot_dim
action_dim = 2

network = TD3(state_dim, action_dim)
try:
    network.load(file_name, "./pytorch_models")
except Exception:
    raise ValueError("Could not load the stored multi-agent model parameters")

test_state = load_test_state() or {}
episode_num = test_state.get("episode_num", 0)
total_env_steps = test_state.get("total_env_steps", 0)
total_agent_samples = test_state.get("total_agent_samples", 0)
success_count = test_state.get("success_count", 0)
collision_count = test_state.get("collision_count", 0)
unresolved_count = test_state.get("unresolved_count", 0)
full_success_count = test_state.get("full_success_count", 0)
timeout_episode_count = test_state.get("timeout_episode_count", 0)
success_hist = test_state.get("success_hist", [0] * (len(agent_names) + 1))
collision_hist = test_state.get("collision_hist", [0] * (len(agent_names) + 1))
case_stats = test_state.get("case_stats", {})
recent_rewards = []
recent_success_rates = []
recent_collision_rates = []
recent_unresolved_rates = []
recent_full_success = []
recent_timeout_episodes = []
log_dir = make_test_run_dir()
writer = SummaryWriter(log_dir=log_dir)

print("==============================================")
print("Test version: multi-agent-eval-v1-headless")
print("Test process PID:", os.getpid())
print("Launchfile:", launchfile)
print("Model file:", file_name)
print("Scenario mode:", scenario_mode)
print("Seed:", seed)
print("Device:", device)
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
print("Agent names:", ", ".join(agent_names))
print("TensorBoard log dir:", log_dir)
print("State path:", state_path)
print("Resume mode:", resume_testing)
print("Starting episode:", episode_num)
print("Starting env steps:", total_env_steps)
print("Starting agent samples:", total_agent_samples)
print("Target test episodes:", target_test_episodes or "unlimited")
if scenario_mode == "curriculum":
    print("Case-level stats enabled")
if trace_failures:
    print("Failure trace mode:", trace_failure_mode)
    print("Failure trace window steps:", trace_window_steps)
    print("Failure trace dir:", trace_dir)
print("==============================================")

states = env.reset()
episode_case_name = current_case_name(env)
active_mask = [True] * len(agent_names)
episode_done = False
episode_env_steps = 0
episode_agent_samples = 0
episode_rewards = np.zeros(len(agent_names), dtype=np.float32)
episode_success_flags = np.zeros(len(agent_names), dtype=np.int32)
episode_collision_flags = np.zeros(len(agent_names), dtype=np.int32)
episode_final_distances = {name: None for name in agent_names}
episode_start_time = time.time()
episode_trace = deque(maxlen=trace_window_steps) if trace_failures else None

while True:
    env_actions = []

    for idx, state in enumerate(states):
        if not active_mask[idx]:
            env_actions.append([0.0, 0.0])
            continue

        action = network.get_action(np.array(state))
        env_actions.append([(action[0] + 1) / 2, action[1]])

    next_states, rewards, dones, targets, collisions = env.step(env_actions, active_mask)
    total_env_steps += 1
    step_agents = env.last_step_info["agents"]
    if trace_failures:
        episode_trace.append(
            build_trace_step(
                episode_env_steps + 1,
                env_actions,
                active_mask,
                next_states,
                rewards,
                step_agents,
            )
        )

    truncated = episode_env_steps + 1 == max_ep
    for idx in range(len(agent_names)):
        if not active_mask[idx]:
            continue

        episode_rewards[idx] += rewards[idx]
        episode_agent_samples += 1
        total_agent_samples += 1
        episode_success_flags[idx] = max(episode_success_flags[idx], int(targets[idx]))
        episode_collision_flags[idx] = max(
            episode_collision_flags[idx], int(collisions[idx])
        )
        episode_final_distances[agent_names[idx]] = step_agents[agent_names[idx]][
            "distance"
        ]

        if dones[idx] or truncated:
            active_mask[idx] = False

    states = next_states
    episode_env_steps += 1
    if truncated or not any(active_mask):
        episode_done = True

    if not episode_done:
        continue

    episode_num += 1
    elapsed = time.time() - episode_start_time
    steps_per_sec = episode_agent_samples / elapsed if elapsed > 0 else 0.0
    success_rate = float(np.mean(episode_success_flags))
    collision_rate = float(np.mean(episode_collision_flags))
    episode_success_count = int(np.sum(episode_success_flags))
    episode_collision_count = int(np.sum(episode_collision_flags))
    episode_unresolved_count = max(
        len(agent_names) - episode_success_count - episode_collision_count, 0
    )
    unresolved_rate = episode_unresolved_count / len(agent_names)
    full_success = int(np.sum(episode_success_flags) == len(agent_names))
    timeout_episode = int(episode_env_steps >= max_ep)
    mean_reward = float(np.mean(episode_rewards))
    mean_final_distance = float(
        np.mean(
            [
                episode_final_distances[name]
                for name in agent_names
                if episode_final_distances[name] is not None
            ]
        )
    )
    update_case_stats(
        case_stats,
        episode_case_name,
        episode_success_count,
        episode_collision_count,
        episode_unresolved_count,
        full_success,
        timeout_episode,
        episode_env_steps,
        mean_final_distance,
    )

    success_count += episode_success_count
    collision_count += episode_collision_count
    unresolved_count += episode_unresolved_count
    full_success_count += full_success
    timeout_episode_count += timeout_episode
    if episode_success_count < len(success_hist):
        success_hist[episode_success_count] += 1
    if episode_collision_count < len(collision_hist):
        collision_hist[episode_collision_count] += 1
    recent_rewards.append(mean_reward)
    recent_success_rates.append(success_rate)
    recent_collision_rates.append(collision_rate)
    recent_unresolved_rates.append(unresolved_rate)
    recent_full_success.append(full_success)
    recent_timeout_episodes.append(timeout_episode)

    avg_reward = float(np.mean(recent_rewards[-print_every_episodes:]))
    avg_success = float(np.mean(recent_success_rates[-print_every_episodes:]))
    avg_collision = float(np.mean(recent_collision_rates[-print_every_episodes:]))
    avg_unresolved = float(np.mean(recent_unresolved_rates[-print_every_episodes:]))
    avg_full_success = float(np.mean(recent_full_success[-print_every_episodes:]))
    avg_timeout_episode = float(
        np.mean(recent_timeout_episodes[-print_every_episodes:])
    )

    if should_trace_episode(timeout_episode, full_success, episode_unresolved_count):
        write_failure_trace(
            episode_num,
            episode_env_steps,
            episode_agent_samples,
            mean_reward,
            episode_success_flags,
            episode_collision_flags,
            episode_final_distances,
            episode_unresolved_count,
            full_success,
            timeout_episode,
            episode_trace,
        )

    print(
        "Episode %i complete | case=%s | env_steps=%i | agent_samples=%i | episode_env_steps=%i | "
        "episode_agent_samples=%i | mean_reward=%.3f | success=%i/%i | collision=%i/%i | "
        "unresolved=%i/%i | full_success=%i | timeout=%i | "
        "mean_final_distance=%.3f | samples/sec=%.3f"
        % (
            episode_num,
            episode_case_name,
            total_env_steps,
            total_agent_samples,
            episode_env_steps,
            episode_agent_samples,
            mean_reward,
            episode_success_count,
            len(agent_names),
            episode_collision_count,
            len(agent_names),
            episode_unresolved_count,
            len(agent_names),
            full_success,
            timeout_episode,
            mean_final_distance,
            steps_per_sec,
        )
    )

    if episode_num % print_every_episodes == 0:
        print(
            "Recent %i episodes | avg_reward=%.3f | success_rate=%.3f | collision_rate=%.3f | "
            "unresolved_rate=%.3f | full_success_rate=%.3f | timeout_episode_rate=%.3f | "
            "total_success=%i | total_collision=%i | total_unresolved=%i | "
            "total_full_success=%i | timeout_episodes=%i | success_hist=%s | collision_hist=%s"
            % (
                print_every_episodes,
                avg_reward,
                avg_success,
                avg_collision,
                avg_unresolved,
                avg_full_success,
                avg_timeout_episode,
                success_count,
                collision_count,
                unresolved_count,
                full_success_count,
                timeout_episode_count,
                success_hist,
                collision_hist,
            )
        )
        if scenario_mode == "curriculum":
            print_case_stats(case_stats)

    writer.add_scalar("test/episode_mean_reward", mean_reward, episode_num)
    writer.add_scalar("test/episode_success_rate", success_rate, episode_num)
    writer.add_scalar("test/episode_collision_rate", collision_rate, episode_num)
    writer.add_scalar("test/episode_unresolved_rate", unresolved_rate, episode_num)
    writer.add_scalar("test/episode_full_success", full_success, episode_num)
    writer.add_scalar("test/episode_timeout", timeout_episode, episode_num)
    writer.add_scalar("test/mean_final_distance", mean_final_distance, episode_num)
    writer.add_scalar("test/samples_per_sec", steps_per_sec, episode_num)
    writer.add_scalar("test/recent_avg_reward", avg_reward, episode_num)
    writer.add_scalar("test/recent_success_rate", avg_success, episode_num)
    writer.add_scalar("test/recent_collision_rate", avg_collision, episode_num)
    writer.add_scalar("test/recent_unresolved_rate", avg_unresolved, episode_num)
    writer.add_scalar("test/recent_full_success_rate", avg_full_success, episode_num)
    writer.add_scalar(
        "test/recent_timeout_episode_rate", avg_timeout_episode, episode_num
    )
    writer.flush()

    save_test_state(
        {
            "episode_num": episode_num,
            "total_env_steps": total_env_steps,
            "total_agent_samples": total_agent_samples,
            "success_count": success_count,
            "collision_count": collision_count,
            "unresolved_count": unresolved_count,
            "full_success_count": full_success_count,
            "timeout_episode_count": timeout_episode_count,
            "success_hist": success_hist,
            "collision_hist": collision_hist,
            "case_stats": case_stats,
            "last_episode_mean_reward": mean_reward,
        }
    )
    append_stats(
        [
            episode_num,
            total_env_steps,
            total_agent_samples,
            episode_env_steps,
            episode_agent_samples,
            mean_reward,
            episode_success_count,
            episode_collision_count,
            full_success,
            mean_final_distance,
            episode_unresolved_count,
            timeout_episode,
            episode_case_name,
        ]
    )

    if target_test_episodes and episode_num >= target_test_episodes:
        print(
            "Target test episodes reached | episode_num=%i | target=%i"
            % (episode_num, target_test_episodes)
        )
        writer.close()
        break

    states = env.reset()
    episode_case_name = current_case_name(env)
    active_mask = [True] * len(agent_names)
    episode_done = False
    episode_env_steps = 0
    episode_agent_samples = 0
    episode_rewards = np.zeros(len(agent_names), dtype=np.float32)
    episode_success_flags = np.zeros(len(agent_names), dtype=np.int32)
    episode_collision_flags = np.zeros(len(agent_names), dtype=np.int32)
    episode_final_distances = {name: None for name in agent_names}
    episode_start_time = time.time()
    episode_trace = deque(maxlen=trace_window_steps) if trace_failures else None
