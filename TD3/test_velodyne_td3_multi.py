import os
import socket
import time
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
seed = 0
max_ep = 300
target_test_episodes = int(os.environ.get("DRL_MULTI_TEST_TARGET_EPISODES", "0"))
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
print_every_episodes = 10
environment_dim = 20
robot_dim = 4
agent_names = ["r1", "r2"]


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


env = MultiAgentGazeboEnv(
    launchfile,
    environment_dim,
    agent_names=agent_names,
    cooperative_reward=False,
    robot_safe_distance=0.0,
    weak_coupling_layout=True,
)
time.sleep(5)
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
full_success_count = test_state.get("full_success_count", 0)
recent_rewards = []
recent_success_rates = []
recent_collision_rates = []
recent_full_success = []
log_dir = make_test_run_dir()
writer = SummaryWriter(log_dir=log_dir)

print("==============================================")
print("Test version: multi-agent-eval-v1-headless")
print("Test process PID:", os.getpid())
print("Launchfile:", launchfile)
print("Model file:", file_name)
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
print("==============================================")

states = env.reset()
active_mask = [True] * len(agent_names)
episode_done = False
episode_env_steps = 0
episode_agent_samples = 0
episode_rewards = np.zeros(len(agent_names), dtype=np.float32)
episode_success_flags = np.zeros(len(agent_names), dtype=np.int32)
episode_collision_flags = np.zeros(len(agent_names), dtype=np.int32)
episode_final_distances = {name: None for name in agent_names}
episode_start_time = time.time()

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
    full_success = int(np.sum(episode_success_flags) == len(agent_names))
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

    success_count += int(np.sum(episode_success_flags))
    collision_count += int(np.sum(episode_collision_flags))
    full_success_count += full_success
    recent_rewards.append(mean_reward)
    recent_success_rates.append(success_rate)
    recent_collision_rates.append(collision_rate)
    recent_full_success.append(full_success)

    avg_reward = float(np.mean(recent_rewards[-print_every_episodes:]))
    avg_success = float(np.mean(recent_success_rates[-print_every_episodes:]))
    avg_collision = float(np.mean(recent_collision_rates[-print_every_episodes:]))
    avg_full_success = float(np.mean(recent_full_success[-print_every_episodes:]))

    print(
        "Episode %i complete | env_steps=%i | agent_samples=%i | episode_env_steps=%i | "
        "episode_agent_samples=%i | mean_reward=%.3f | success=%i/%i | collision=%i/%i | "
        "mean_final_distance=%.3f | samples/sec=%.3f"
        % (
            episode_num,
            total_env_steps,
            total_agent_samples,
            episode_env_steps,
            episode_agent_samples,
            mean_reward,
            int(np.sum(episode_success_flags)),
            len(agent_names),
            int(np.sum(episode_collision_flags)),
            len(agent_names),
            mean_final_distance,
            steps_per_sec,
        )
    )

    if episode_num % print_every_episodes == 0:
        print(
            "Recent %i episodes | avg_reward=%.3f | success_rate=%.3f | collision_rate=%.3f | "
            "full_success_rate=%.3f | total_success=%i | total_collision=%i | total_full_success=%i"
            % (
                print_every_episodes,
                avg_reward,
                avg_success,
                avg_collision,
                avg_full_success,
                success_count,
                collision_count,
                full_success_count,
            )
        )

    writer.add_scalar("test/episode_mean_reward", mean_reward, episode_num)
    writer.add_scalar("test/episode_success_rate", success_rate, episode_num)
    writer.add_scalar("test/episode_collision_rate", collision_rate, episode_num)
    writer.add_scalar("test/episode_full_success", full_success, episode_num)
    writer.add_scalar("test/mean_final_distance", mean_final_distance, episode_num)
    writer.add_scalar("test/samples_per_sec", steps_per_sec, episode_num)
    writer.add_scalar("test/recent_avg_reward", avg_reward, episode_num)
    writer.add_scalar("test/recent_success_rate", avg_success, episode_num)
    writer.add_scalar("test/recent_collision_rate", avg_collision, episode_num)
    writer.add_scalar("test/recent_full_success_rate", avg_full_success, episode_num)
    writer.flush()

    save_test_state(
        {
            "episode_num": episode_num,
            "total_env_steps": total_env_steps,
            "total_agent_samples": total_agent_samples,
            "success_count": success_count,
            "collision_count": collision_count,
            "full_success_count": full_success_count,
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
            int(np.sum(episode_success_flags)),
            int(np.sum(episode_collision_flags)),
            full_success,
            mean_final_distance,
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
    active_mask = [True] * len(agent_names)
    episode_done = False
    episode_env_steps = 0
    episode_agent_samples = 0
    episode_rewards = np.zeros(len(agent_names), dtype=np.float32)
    episode_success_flags = np.zeros(len(agent_names), dtype=np.int32)
    episode_collision_flags = np.zeros(len(agent_names), dtype=np.int32)
    episode_final_distances = {name: None for name in agent_names}
    episode_start_time = time.time()
