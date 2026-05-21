import os
import socket
import sys
import time
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from numpy import inf
from torch.utils.tensorboard import SummaryWriter

from multi_agent_velodyne_env import MultiAgentGazeboEnv
from replay_buffer import ReplayBuffer


def evaluate(network, env, epoch, eval_episodes=10):
    previous_mode = env.cooperative_reward
    env.set_cooperative_reward(False)

    total_reward = 0.0
    total_collisions = 0
    total_targets = 0
    total_agents = eval_episodes * env.num_agents
    total_episode_steps = 0.0
    total_final_distance = 0.0

    for _ in range(eval_episodes):
        states = env.reset()
        active_mask = [True] * env.num_agents
        count = 0
        while any(active_mask) and count < max_ep:
            actions = []
            for idx in range(env.num_agents):
                if active_mask[idx]:
                    action = network.get_action(np.array(states[idx]))
                    actions.append([(action[0] + 1) / 2, action[1]])
                else:
                    actions.append([0.0, 0.0])

            next_states, rewards, dones, targets, collisions = env.step(
                actions, active_mask
            )
            total_reward += sum(rewards)
            total_collisions += sum(int(flag) for flag in collisions)
            total_targets += sum(int(flag) for flag in targets)

            for idx, done in enumerate(dones):
                if active_mask[idx] and done:
                    active_mask[idx] = False

            states = next_states
            count += 1

        total_episode_steps += count
        for name in env.agent_names:
            distance = env.last_step_info["agents"][name]["distance"]
            if distance is not None:
                total_final_distance += distance

    avg_reward = total_reward / total_agents
    success_rate = total_targets / total_agents
    collision_rate = total_collisions / total_agents
    avg_episode_steps = total_episode_steps / eval_episodes
    avg_final_distance = total_final_distance / total_agents

    print("..............................................")
    print(
        "Multi-Agent Eval Epoch %i | avg_reward=%.3f | success_rate=%.3f | "
        "collision_rate=%.3f | avg_env_steps=%.1f | avg_final_distance=%.3f"
        % (
            epoch,
            avg_reward,
            success_rate,
            collision_rate,
            avg_episode_steps,
            avg_final_distance,
        )
    )
    print("..............................................")

    env.set_cooperative_reward(previous_mode)
    return {
        "avg_reward": avg_reward,
        "success_rate": success_rate,
        "collision_rate": collision_rate,
        "avg_episode_steps": avg_episode_steps,
        "avg_final_distance": avg_final_distance,
    }


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


class Critic(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(Critic, self).__init__()

        self.layer_1 = nn.Linear(state_dim, 800)
        self.layer_2_s = nn.Linear(800, 600)
        self.layer_2_a = nn.Linear(action_dim, 600)
        self.layer_3 = nn.Linear(600, 1)

        self.layer_4 = nn.Linear(state_dim, 800)
        self.layer_5_s = nn.Linear(800, 600)
        self.layer_5_a = nn.Linear(action_dim, 600)
        self.layer_6 = nn.Linear(600, 1)

    def forward(self, s, a):
        s1 = F.relu(self.layer_1(s))
        self.layer_2_s(s1)
        self.layer_2_a(a)
        s11 = torch.mm(s1, self.layer_2_s.weight.data.t())
        s12 = torch.mm(a, self.layer_2_a.weight.data.t())
        s1 = F.relu(s11 + s12 + self.layer_2_a.bias.data)
        q1 = self.layer_3(s1)

        s2 = F.relu(self.layer_4(s))
        self.layer_5_s(s2)
        self.layer_5_a(a)
        s21 = torch.mm(s2, self.layer_5_s.weight.data.t())
        s22 = torch.mm(a, self.layer_5_a.weight.data.t())
        s2 = F.relu(s21 + s22 + self.layer_5_a.bias.data)
        q2 = self.layer_6(s2)
        return q1, q2


class TD3(object):
    def __init__(self, state_dim, action_dim, max_action, log_dir=None, critic_state_dim=None):
        self.state_dim = state_dim
        self.critic_state_dim = critic_state_dim or state_dim
        self.actor = Actor(state_dim, action_dim).to(device)
        self.actor_target = Actor(state_dim, action_dim).to(device)
        self.actor_target.load_state_dict(self.actor.state_dict())
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters())

        self.critic = Critic(self.critic_state_dim, action_dim).to(device)
        self.critic_target = Critic(self.critic_state_dim, action_dim).to(device)
        self.critic_target.load_state_dict(self.critic.state_dict())
        self.critic_optimizer = torch.optim.Adam(self.critic.parameters())

        self.max_action = max_action
        self.writer = SummaryWriter(log_dir=log_dir)
        self.iter_count = 0

    def get_action(self, state):
        state = torch.Tensor(state.reshape(1, -1)).to(device)
        return self.actor(state).cpu().data.numpy().flatten()

    def train(
        self,
        replay_buffer,
        iterations,
        batch_size=100,
        discount=1,
        tau=0.005,
        policy_noise=0.2,
        noise_clip=0.5,
        policy_freq=2,
    ):
        av_Q = 0
        max_Q = -inf
        av_loss = 0
        for it in range(iterations):
            (
                batch_states,
                batch_actions,
                batch_rewards,
                batch_dones,
                batch_next_states,
            ) = replay_buffer.sample_batch(batch_size)
            state = torch.Tensor(batch_states).to(device)
            next_state = torch.Tensor(batch_next_states).to(device)
            action = torch.Tensor(batch_actions).to(device)
            reward = torch.Tensor(batch_rewards).to(device)
            done = torch.Tensor(batch_dones).to(device)

            next_action = self.actor_target(next_state)
            noise = torch.Tensor(batch_actions).data.normal_(0, policy_noise).to(device)
            noise = noise.clamp(-noise_clip, noise_clip)
            next_action = (next_action + noise).clamp(-self.max_action, self.max_action)

            target_Q1, target_Q2 = self.critic_target(next_state, next_action)
            target_Q = torch.min(target_Q1, target_Q2)
            av_Q += torch.mean(target_Q)
            max_Q = max(max_Q, torch.max(target_Q))
            target_Q = reward + ((1 - done) * discount * target_Q).detach()

            current_Q1, current_Q2 = self.critic(state, action)
            loss = F.mse_loss(current_Q1, target_Q) + F.mse_loss(current_Q2, target_Q)

            self.critic_optimizer.zero_grad()
            loss.backward()
            self.critic_optimizer.step()

            if it % policy_freq == 0:
                actor_grad, _ = self.critic(state, self.actor(state))
                actor_grad = -actor_grad.mean()
                self.actor_optimizer.zero_grad()
                actor_grad.backward()
                self.actor_optimizer.step()

                for param, target_param in zip(
                    self.actor.parameters(), self.actor_target.parameters()
                ):
                    target_param.data.copy_(
                        tau * param.data + (1 - tau) * target_param.data
                    )

                for param, target_param in zip(
                    self.critic.parameters(), self.critic_target.parameters()
                ):
                    target_param.data.copy_(
                        tau * param.data + (1 - tau) * target_param.data
                    )

            av_loss += loss

        self.iter_count += 1
        self.writer.add_scalar("loss", av_loss / iterations, self.iter_count)
        self.writer.add_scalar("Av. Q", av_Q / iterations, self.iter_count)
        self.writer.add_scalar("Max. Q", max_Q, self.iter_count)

    def train_local_critic(
        self,
        replay_buffer,
        iterations,
        batch_size=100,
        discount=1,
        tau=0.005,
        policy_noise=0.2,
        noise_clip=0.5,
        policy_freq=2,
    ):
        av_Q = 0
        max_Q = -inf
        av_loss = 0
        for it in range(iterations):
            (
                batch_states,
                batch_critic_states,
                batch_actions,
                batch_rewards,
                batch_dones,
                batch_next_states,
                batch_next_critic_states,
            ) = replay_buffer.sample_local_critic_batch(batch_size)
            state = torch.Tensor(batch_states).to(device)
            critic_state = torch.Tensor(batch_critic_states).to(device)
            next_state = torch.Tensor(batch_next_states).to(device)
            next_critic_state = torch.Tensor(batch_next_critic_states).to(device)
            action = torch.Tensor(batch_actions).to(device)
            reward = torch.Tensor(batch_rewards).to(device)
            done = torch.Tensor(batch_dones).to(device)

            next_action = self.actor_target(next_state)
            noise = torch.Tensor(batch_actions).data.normal_(0, policy_noise).to(device)
            noise = noise.clamp(-noise_clip, noise_clip)
            next_action = (next_action + noise).clamp(-self.max_action, self.max_action)

            target_Q1, target_Q2 = self.critic_target(next_critic_state, next_action)
            target_Q = torch.min(target_Q1, target_Q2)
            av_Q += torch.mean(target_Q)
            max_Q = max(max_Q, torch.max(target_Q))
            target_Q = reward + ((1 - done) * discount * target_Q).detach()

            current_Q1, current_Q2 = self.critic(critic_state, action)
            loss = F.mse_loss(current_Q1, target_Q) + F.mse_loss(current_Q2, target_Q)

            self.critic_optimizer.zero_grad()
            loss.backward()
            self.critic_optimizer.step()

            if it % policy_freq == 0:
                actor_action = self.actor(state)
                actor_grad, _ = self.critic(critic_state, actor_action)
                actor_grad = -actor_grad.mean()
                self.actor_optimizer.zero_grad()
                actor_grad.backward()
                self.actor_optimizer.step()

                for param, target_param in zip(
                    self.actor.parameters(), self.actor_target.parameters()
                ):
                    target_param.data.copy_(
                        tau * param.data + (1 - tau) * target_param.data
                    )

                for param, target_param in zip(
                    self.critic.parameters(), self.critic_target.parameters()
                ):
                    target_param.data.copy_(
                        tau * param.data + (1 - tau) * target_param.data
                    )

            av_loss += loss

        self.iter_count += 1
        self.writer.add_scalar("loss", av_loss / iterations, self.iter_count)
        self.writer.add_scalar("Av. Q", av_Q / iterations, self.iter_count)
        self.writer.add_scalar("Max. Q", max_Q, self.iter_count)

    def save(self, filename, directory):
        torch.save(self.actor.state_dict(), "%s/%s_actor.pth" % (directory, filename))
        torch.save(self.critic.state_dict(), "%s/%s_critic.pth" % (directory, filename))

    def load(self, filename, directory):
        self.actor.load_state_dict(
            torch.load("%s/%s_actor.pth" % (directory, filename), map_location=device)
        )
        self.critic.load_state_dict(
            torch.load("%s/%s_critic.pth" % (directory, filename), map_location=device)
        )

    def load_actor(self, filename, directory):
        actor_state = torch.load(
            "%s/%s_actor.pth" % (directory, filename), map_location=device
        )
        self.actor.load_state_dict(actor_state)
        self.actor_target.load_state_dict(actor_state)

    def state_dict(self):
        return {
            "actor": self.actor.state_dict(),
            "actor_target": self.actor_target.state_dict(),
            "actor_optimizer": self.actor_optimizer.state_dict(),
            "critic": self.critic.state_dict(),
            "critic_target": self.critic_target.state_dict(),
            "critic_optimizer": self.critic_optimizer.state_dict(),
            "iter_count": self.iter_count,
            "log_dir": self.writer.log_dir,
            "max_action": self.max_action,
            "state_dim": self.state_dim,
            "critic_state_dim": self.critic_state_dim,
        }

    def load_state_dict(self, state):
        self.actor.load_state_dict(state["actor"])
        self.actor_target.load_state_dict(state["actor_target"])
        self.actor_optimizer.load_state_dict(state["actor_optimizer"])
        self.critic.load_state_dict(state["critic"])
        self.critic_target.load_state_dict(state["critic_target"])
        self.critic_optimizer.load_state_dict(state["critic_optimizer"])
        self.iter_count = state["iter_count"]


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_float(name, default=None):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def env_int(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


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


seed = 0
eval_freq = 5e3
max_ep = 300
eval_ep = int(os.environ.get("DRL_MULTI_EVAL_EPISODES", "10"))
max_epochs = env_int("DRL_MULTI_MAX_EPOCHS", 0)
max_timesteps = 5e6
expl_noise = 1.0
expl_decay_steps = 500000
expl_min = 0.1
batch_size = 40
discount = 0.99999
tau = 0.005
policy_noise = 0.2
noise_clip = 0.5
policy_freq = 2
buffer_size = 1e6
agent_names = make_agent_names()
use_dynamic_reward = env_flag("DRL_MULTI_USE_DYNAMIC_REWARD", False)
cooperative_reward_self_weight = env_float("DRL_MULTI_REWARD_SELF_WEIGHT", None)
use_local_critic = env_flag("DRL_MULTI_USE_LOCAL_CRITIC", False)
local_critic_geometry_only = env_flag(
    "DRL_MULTI_LOCAL_CRITIC_GEOMETRY_ONLY", False
)
local_critic_max_agents = env_int("DRL_MULTI_LOCAL_CRITIC_MAX_AGENTS", 10)
local_critic_max_neighbors = max(local_critic_max_agents - 1, 1)
local_critic_feature_dim = 5 if local_critic_geometry_only else 7
use_distance_weighted_reward = env_flag(
    "DRL_MULTI_USE_DISTANCE_WEIGHTED_REWARD", False
)
cooperative_reward_sigma = env_float("DRL_MULTI_REWARD_SIGMA", 2.0)
base_file_name = "TD3_velodyne_multi_v4"
file_name = os.environ.get(
    "DRL_MULTI_TRAIN_FILE_NAME",
    f"{base_file_name}_coop" if use_dynamic_reward else base_file_name,
)
save_model = True
load_model = env_flag("DRL_MULTI_LOAD_MODEL", False)
load_model_name = os.environ.get("DRL_MULTI_LOAD_MODEL_NAME", file_name)
random_near_obstacle = False
resume_training = True
launchfile = os.environ.get(
    "DRL_MULTI_TRAIN_LAUNCHFILE", "multi_robot_scenario_multi_2.launch"
)
checkpoint_dir = "./checkpoints"
checkpoint_path = os.path.join(checkpoint_dir, f"{file_name}_latest.pt")
best_checkpoint_path = os.path.join(checkpoint_dir, f"{file_name}_best.pt")
checkpoint_interval_episodes = 10
status_interval_episodes = 5
training_version = (
    os.environ.get("DRL_MULTI_TRAINING_VERSION")
    or (
        "multi-agent-shared-policy-v4-coop"
        if use_dynamic_reward
        else "multi-agent-shared-policy-v4"
    )
)

if not os.path.exists("./results"):
    os.makedirs("./results")
if save_model and not os.path.exists("./pytorch_models"):
    os.makedirs("./pytorch_models")
if not os.path.exists(checkpoint_dir):
    os.makedirs(checkpoint_dir)


def make_run_log_dir():
    timestamp = datetime.now().strftime("%b%d_%H-%M-%S")
    prefix = "multi_coop" if use_dynamic_reward else "multi"
    return os.path.join("runs", f"{prefix}_{timestamp}_{socket.gethostname()}")


def save_training_checkpoint(
    network,
    replay_buffer,
    evaluations,
    timestep,
    env_step_count,
    timesteps_since_eval,
    episode_num,
    epoch,
    expl_noise_value,
    best_eval_summary=None,
    best_epoch=None,
    path=checkpoint_path,
):
    torch.save(
        {
            "network": network.state_dict(),
            "replay_buffer": replay_buffer.state_dict(),
            "evaluations": evaluations,
            "timestep": timestep,
            "env_step_count": env_step_count,
            "timesteps_since_eval": timesteps_since_eval,
            "episode_num": episode_num,
            "epoch": epoch,
            "expl_noise": expl_noise_value,
            "best_eval_summary": best_eval_summary,
            "best_epoch": best_epoch,
        },
        path,
    )


def load_training_checkpoint():
    if not (resume_training and os.path.exists(checkpoint_path)):
        return None
    return torch.load(checkpoint_path, map_location="cpu")


environment_dim = 20
robot_dim = 4
env = MultiAgentGazeboEnv(
    launchfile,
    environment_dim,
    agent_names=agent_names,
    cooperative_reward=use_dynamic_reward,
    cooperative_reward_self_weight=cooperative_reward_self_weight,
    cooperative_reward_distance_weighted=use_distance_weighted_reward,
    cooperative_reward_sigma=cooperative_reward_sigma,
    robot_safe_distance=0.0,
    weak_coupling_layout=True,
)
time.sleep(5)
torch.manual_seed(seed)
np.random.seed(seed)
state_dim = environment_dim + robot_dim
action_dim = 2
max_action = 1
critic_context_dim = local_critic_max_neighbors * local_critic_feature_dim
critic_state_dim = state_dim + critic_context_dim if use_local_critic else state_dim

checkpoint = load_training_checkpoint()
log_dir = checkpoint["network"]["log_dir"] if checkpoint else make_run_log_dir()

network = TD3(
    state_dim,
    action_dim,
    max_action,
    log_dir=log_dir,
    critic_state_dim=critic_state_dim,
)
replay_buffer = ReplayBuffer(buffer_size, seed)

if checkpoint:
    network.load_state_dict(checkpoint["network"])
    replay_buffer.load_state_dict(checkpoint["replay_buffer"])
    print("Resumed multi-agent training from checkpoint:", checkpoint_path)
elif load_model:
    try:
        if use_local_critic:
            network.load_actor(load_model_name, "./pytorch_models")
            print("Loaded initial actor parameters from:", load_model_name)
            print("Local critic is newly initialized because critic input dim changed.")
        else:
            network.load(load_model_name, "./pytorch_models")
            print("Loaded initial model parameters from:", load_model_name)
    except Exception:
        print("Could not load the stored model parameters, initializing randomly")

evaluations = checkpoint["evaluations"] if checkpoint else []
timestep = checkpoint["timestep"] if checkpoint else 0
env_step_count = checkpoint["env_step_count"] if checkpoint else 0
timesteps_since_eval = checkpoint["timesteps_since_eval"] if checkpoint else 0
episode_num = checkpoint["episode_num"] if checkpoint else 0
episode_done = True
epoch = checkpoint["epoch"] if checkpoint else 1
count_rand_actions = [0 for _ in agent_names]
random_actions = [np.zeros(2) for _ in agent_names]
expl_noise = checkpoint["expl_noise"] if checkpoint else expl_noise
best_eval_summary = checkpoint.get("best_eval_summary") if checkpoint else None
best_epoch = checkpoint.get("best_epoch") if checkpoint else None
skip_episode_summary_once = checkpoint is not None
train_start_time = time.time()

print("==============================================")
print("Training version:", training_version)
print("Training process PID:", os.getpid())
print("Launchfile:", launchfile)
print("Device:", device)
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
print("Agent names:", ", ".join(agent_names))
print("Cooperative reward:", use_dynamic_reward)
print("Cooperative reward self weight:", cooperative_reward_self_weight)
print("Distance-weighted reward:", use_distance_weighted_reward)
print("Distance reward sigma:", cooperative_reward_sigma)
print("Local critic enabled:", use_local_critic)
print("Local critic geometry only:", local_critic_geometry_only)
print("Actor state dim:", state_dim)
print("Critic state dim:", critic_state_dim)
print("Local critic max neighbors:", local_critic_max_neighbors)
print("Local critic context dim:", critic_context_dim)
print("Eval episodes:", eval_ep)
print("Max epochs:", max_epochs or "unlimited")
print("TensorBoard log dir:", log_dir)
print("Checkpoint path:", checkpoint_path)
print("Best checkpoint path:", best_checkpoint_path)
print("Model prefix:", file_name)
print("Checkpoint interval episodes:", checkpoint_interval_episodes)
print("Resume mode:", resume_training)
print("Starting agent samples:", timestep)
print("Starting env steps:", env_step_count)
print("Starting epoch:", epoch)
print("==============================================")

last_eval_summary = None


def combine_critic_state(state, context):
    return np.concatenate(
        [np.array(state, dtype=np.float32), np.array(context, dtype=np.float32)]
    )


def context_stats(contexts):
    if not contexts:
        return 0.0, 0.0
    mask_offset = local_critic_feature_dim - 1
    masks = [
        np.array(context, dtype=np.float32)[mask_offset::local_critic_feature_dim]
        for context in contexts
    ]
    counts = [float(np.sum(mask)) for mask in masks]
    return float(np.mean(counts)), float(np.max(counts))


def is_better_eval(candidate, current_best):
    if current_best is None:
        return True
    candidate_key = (
        candidate["success_rate"],
        -candidate["collision_rate"],
        candidate["avg_reward"],
        -candidate["avg_final_distance"],
    )
    best_key = (
        current_best["success_rate"],
        -current_best["collision_rate"],
        current_best["avg_reward"],
        -current_best["avg_final_distance"],
    )
    return candidate_key > best_key

while timestep < max_timesteps:
    if episode_done:
        if timestep != 0 and not skip_episode_summary_once:
            train_iterations = max(episode_timesteps, 1)
            if use_local_critic:
                network.train_local_critic(
                    replay_buffer,
                    train_iterations,
                    batch_size,
                    discount,
                    tau,
                    policy_noise,
                    noise_clip,
                    policy_freq,
                )
            else:
                network.train(
                    replay_buffer,
                    train_iterations,
                    batch_size,
                    discount,
                    tau,
                    policy_noise,
                    noise_clip,
                    policy_freq,
                )
            elapsed = time.time() - train_start_time
            steps_per_sec = timestep / elapsed if elapsed > 0 else 0.0
            step_agents = env.last_step_info["agents"]
            success_count = int(sum(episode_success_flags))
            collision_count = int(sum(episode_collision_flags))
            mean_final_distance = float(
                np.mean(
                    [
                        episode_final_distances[name]
                        for name in agent_names
                        if episode_final_distances[name] is not None
                    ]
                )
            )
            mean_progress = float(
                np.mean([step_agents[name]["progress"] for name in agent_names])
            )
            min_laser = float(
                np.min(
                    [
                        episode_min_lasers[name]
                        for name in agent_names
                        if episode_min_lasers[name] is not None
                    ]
                )
            )
            mean_linear_action = float(
                np.mean(
                    [episode_last_env_actions[name][0] for name in agent_names]
                )
            )
            mean_angular_action = float(
                np.mean([episode_last_env_actions[name][1] for name in agent_names])
            )
            nearest_robot_distances = [
                step_agents[name]["nearest_robot_distance"]
                for name in agent_names
                if step_agents[name]["nearest_robot_distance"] is not None
            ]
            mean_nearest_robot_distance = (
                float(np.mean(nearest_robot_distances))
                if nearest_robot_distances
                else float("nan")
            )
            raw_rewards = [step_agents[name]["raw_reward"] for name in agent_names]
            adjusted_rewards = [step_agents[name]["reward"] for name in agent_names]
            coop_neighbor_counts = [
                len(step_agents[name]["reward_neighbors"]) for name in agent_names
            ]
            mean_context_neighbors, max_context_neighbors = context_stats(
                episode_last_neighbor_contexts
            )
            coop_active_agents = sum(1 for count in coop_neighbor_counts if count > 0)
            mean_raw_reward = float(np.mean(raw_rewards))
            mean_adjusted_reward = float(np.mean(adjusted_rewards))
            mean_coop_neighbors = float(np.mean(coop_neighbor_counts))
            print(
                "Episode %i complete | agent_samples=%i | env_steps=%i | "
                "episode_env_steps=%i | episode_agent_samples=%i | mean_reward=%.3f | "
                "success=%i/%i | collision=%i/%i | mean_final_distance=%.3f | "
                "mean_progress=%.4f | min_laser=%.3f | mean_lin=%.3f | mean_ang=%.3f | "
                "mean_robot_dist=%.3f | raw_reward=%.3f | adjusted_reward=%.3f | "
                "coop_agents=%i/%i | mean_coop_neighbors=%.2f | "
                "context_neighbors_mean=%.2f | context_neighbors_max=%.0f | "
                "expl_noise=%.4f | "
                "replay=%i | samples/sec=%.3f"
                % (
                    episode_num,
                    timestep,
                    env_step_count,
                    episode_timesteps,
                    episode_sample_count,
                    float(np.mean(episode_rewards)),
                    success_count,
                    len(agent_names),
                    collision_count,
                    len(agent_names),
                    mean_final_distance,
                    mean_progress,
                    min_laser,
                    mean_linear_action,
                    mean_angular_action,
                    mean_nearest_robot_distance,
                    mean_raw_reward,
                    mean_adjusted_reward,
                    coop_active_agents,
                    len(agent_names),
                    mean_coop_neighbors,
                    mean_context_neighbors,
                    max_context_neighbors,
                    expl_noise,
                    replay_buffer.size(),
                    steps_per_sec,
                )
            )
            if episode_num % status_interval_episodes == 0:
                print(
                    "Status | epoch=%i | next_eval_in=%i agent_samples | "
                    "checkpoint_every=%i episodes | checkpoint=%s | model=%s"
                    % (
                        epoch,
                        int(eval_freq - timesteps_since_eval),
                        checkpoint_interval_episodes,
                        checkpoint_path,
                        file_name,
                    )
                )
            if episode_num % checkpoint_interval_episodes == 0:
                save_training_checkpoint(
                    network,
                    replay_buffer,
                    evaluations,
                    timestep,
                    env_step_count,
                    timesteps_since_eval,
                    episode_num,
                    epoch,
                    expl_noise,
                    best_eval_summary,
                    best_epoch,
                )
                print("Checkpoint saved:", checkpoint_path)

        if timesteps_since_eval >= eval_freq:
            print(
                "Validating multi-agent policy at agent_samples=%i env_steps=%i"
                % (timestep, env_step_count)
            )
            timesteps_since_eval %= eval_freq
            last_eval_summary = evaluate(
                network=network, env=env, epoch=epoch, eval_episodes=eval_ep
            )
            evaluations.append(
                [
                    last_eval_summary["avg_reward"],
                    last_eval_summary["success_rate"],
                    last_eval_summary["collision_rate"],
                    last_eval_summary["avg_episode_steps"],
                    last_eval_summary["avg_final_distance"],
                ]
            )
            network.writer.add_scalar(
                "eval/avg_reward", last_eval_summary["avg_reward"], epoch
            )
            network.writer.add_scalar(
                "eval/success_rate", last_eval_summary["success_rate"], epoch
            )
            network.writer.add_scalar(
                "eval/collision_rate", last_eval_summary["collision_rate"], epoch
            )
            network.writer.add_scalar(
                "eval/avg_env_steps", last_eval_summary["avg_episode_steps"], epoch
            )
            network.writer.add_scalar(
                "eval/avg_final_distance",
                last_eval_summary["avg_final_distance"],
                epoch,
            )
            network.save(file_name, directory="./pytorch_models")
            np.save("./results/%s" % file_name, evaluations)
            save_training_checkpoint(
                network,
                replay_buffer,
                evaluations,
                timestep,
                env_step_count,
                timesteps_since_eval,
                episode_num,
                epoch,
                expl_noise,
                best_eval_summary,
                best_epoch,
            )
            print("Checkpoint saved:", checkpoint_path)
            if is_better_eval(last_eval_summary, best_eval_summary):
                best_eval_summary = dict(last_eval_summary)
                best_epoch = epoch
                network.save(f"{file_name}_best", directory="./pytorch_models")
                save_training_checkpoint(
                    network,
                    replay_buffer,
                    evaluations,
                    timestep,
                    env_step_count,
                    timesteps_since_eval,
                    episode_num,
                    epoch,
                    expl_noise,
                    best_eval_summary,
                    best_epoch,
                    best_checkpoint_path,
                )
                save_training_checkpoint(
                    network,
                    replay_buffer,
                    evaluations,
                    timestep,
                    env_step_count,
                    timesteps_since_eval,
                    episode_num,
                    epoch,
                    expl_noise,
                    best_eval_summary,
                    best_epoch,
                )
                print(
                    "Best checkpoint updated | epoch=%i | success_rate=%.3f | "
                    "collision_rate=%.3f | avg_reward=%.3f | path=%s"
                    % (
                        best_epoch,
                        best_eval_summary["success_rate"],
                        best_eval_summary["collision_rate"],
                        best_eval_summary["avg_reward"],
                        best_checkpoint_path,
                    )
                )
            epoch += 1
            print(
                "Next epoch will start from %i. Resume keeps this counter in %s"
                % (epoch, checkpoint_path)
            )
            if max_epochs and epoch > max_epochs:
                print(
                    "Max epochs reached | completed_epochs=%i | max_epochs=%i"
                    % (epoch - 1, max_epochs)
                )
                break

        states = env.reset()
        zero_env_actions = [[0.0, 0.0] for _ in agent_names]
        neighbor_contexts = (
            env.build_neighbor_context(
                zero_env_actions,
                max_neighbors=local_critic_max_neighbors,
                include_actions=not local_critic_geometry_only,
            )
            if use_local_critic
            else None
        )
        skip_episode_summary_once = False
        active_mask = [True] * len(agent_names)
        episode_done = False
        episode_rewards = np.zeros(len(agent_names), dtype=np.float32)
        episode_timesteps = 0
        episode_sample_count = 0
        episode_success_flags = np.zeros(len(agent_names), dtype=np.int32)
        episode_collision_flags = np.zeros(len(agent_names), dtype=np.int32)
        episode_final_distances = {name: None for name in agent_names}
        episode_min_lasers = {name: None for name in agent_names}
        episode_last_env_actions = {
            name: np.zeros(action_dim, dtype=np.float32) for name in agent_names
        }
        episode_last_neighbor_contexts = (
            neighbor_contexts
            if use_local_critic
            else [np.zeros(critic_context_dim, dtype=np.float32) for _ in agent_names]
        )
        episode_num += 1

    if expl_noise > expl_min:
        expl_noise = expl_noise - ((1 - expl_min) / expl_decay_steps)

    raw_actions = []
    env_actions = []

    for idx, state in enumerate(states):
        if not active_mask[idx]:
            raw_actions.append(np.zeros(action_dim, dtype=np.float32))
            env_actions.append([0.0, 0.0])
            continue

        action = network.get_action(np.array(state))
        action = (action + np.random.normal(0, expl_noise, size=action_dim)).clip(
            -max_action, max_action
        )

        if random_near_obstacle:
            if (
                np.random.uniform(0, 1) > 0.85
                and min(state[:environment_dim]) < 0.6
                and count_rand_actions[idx] < 1
            ):
                count_rand_actions[idx] = np.random.randint(8, 15)
                random_actions[idx] = np.random.uniform(-1, 1, 2)

            if count_rand_actions[idx] > 0:
                count_rand_actions[idx] -= 1
                action = random_actions[idx].copy()
                action[0] = -1

        raw_actions.append(action)
        env_actions.append([(action[0] + 1) / 2, action[1]])
        episode_last_env_actions[agent_names[idx]] = np.array(
            [(action[0] + 1) / 2, action[1]], dtype=np.float32
        )

    next_states, rewards, dones, targets, collisions = env.step(
        env_actions, active_mask
    )
    next_neighbor_contexts = (
        env.build_neighbor_context(
            env_actions,
            max_neighbors=local_critic_max_neighbors,
            include_actions=not local_critic_geometry_only,
        )
        if use_local_critic
        else None
    )
    env_step_count += 1
    step_agents = env.last_step_info["agents"]

    truncated = episode_timesteps + 1 == max_ep
    for idx in range(len(agent_names)):
        if not active_mask[idx]:
            continue
        done_bool = 0 if truncated else int(dones[idx])
        if use_local_critic:
            replay_buffer.add_local_critic(
                states[idx],
                combine_critic_state(states[idx], neighbor_contexts[idx]),
                raw_actions[idx],
                rewards[idx],
                done_bool,
                next_states[idx],
                combine_critic_state(next_states[idx], next_neighbor_contexts[idx]),
            )
        else:
            replay_buffer.add(
                states[idx], raw_actions[idx], rewards[idx], done_bool, next_states[idx]
            )
        episode_rewards[idx] += rewards[idx]
        episode_sample_count += 1
        episode_success_flags[idx] = max(episode_success_flags[idx], int(targets[idx]))
        episode_collision_flags[idx] = max(
            episode_collision_flags[idx], int(collisions[idx])
        )
        episode_final_distances[agent_names[idx]] = step_agents[agent_names[idx]][
            "distance"
        ]
        min_laser_value = step_agents[agent_names[idx]]["min_laser"]
        if min_laser_value is not None:
            previous_min_laser = episode_min_lasers[agent_names[idx]]
            if previous_min_laser is None:
                episode_min_lasers[agent_names[idx]] = min_laser_value
            else:
                episode_min_lasers[agent_names[idx]] = min(
                    previous_min_laser, min_laser_value
                )
        timestep += 1
        timesteps_since_eval += 1

        if dones[idx] or truncated:
            active_mask[idx] = False

    states = next_states
    if use_local_critic:
        neighbor_contexts = next_neighbor_contexts
        episode_last_neighbor_contexts = next_neighbor_contexts
    episode_timesteps += 1

    if truncated or not any(active_mask):
        episode_done = True

if max_epochs and epoch > max_epochs:
    print("Training stopped after reaching configured max epochs.")
    sys.exit(0)

last_eval_summary = evaluate(network=network, env=env, epoch=epoch, eval_episodes=eval_ep)
evaluations.append(
    [
        last_eval_summary["avg_reward"],
        last_eval_summary["success_rate"],
        last_eval_summary["collision_rate"],
        last_eval_summary["avg_episode_steps"],
        last_eval_summary["avg_final_distance"],
    ]
)
network.writer.add_scalar("eval/avg_reward", last_eval_summary["avg_reward"], epoch)
network.writer.add_scalar(
    "eval/success_rate", last_eval_summary["success_rate"], epoch
)
network.writer.add_scalar(
    "eval/collision_rate", last_eval_summary["collision_rate"], epoch
)
network.writer.add_scalar(
    "eval/avg_env_steps", last_eval_summary["avg_episode_steps"], epoch
)
network.writer.add_scalar(
    "eval/avg_final_distance", last_eval_summary["avg_final_distance"], epoch
)
if save_model:
    network.save("%s" % file_name, directory="./pytorch_models")
np.save("./results/%s" % file_name, evaluations)
save_training_checkpoint(
    network,
    replay_buffer,
    evaluations,
    timestep,
    env_step_count,
    timesteps_since_eval,
    episode_num,
    epoch,
    expl_noise,
    best_eval_summary,
    best_epoch,
)
if is_better_eval(last_eval_summary, best_eval_summary):
    best_eval_summary = dict(last_eval_summary)
    best_epoch = epoch
    network.save(f"{file_name}_best", directory="./pytorch_models")
    save_training_checkpoint(
        network,
        replay_buffer,
        evaluations,
        timestep,
        env_step_count,
        timesteps_since_eval,
        episode_num,
        epoch,
        expl_noise,
        best_eval_summary,
        best_epoch,
        best_checkpoint_path,
    )
    save_training_checkpoint(
        network,
        replay_buffer,
        evaluations,
        timestep,
        env_step_count,
        timesteps_since_eval,
        episode_num,
        epoch,
        expl_noise,
        best_eval_summary,
        best_epoch,
    )
