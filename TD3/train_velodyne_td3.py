import os
import socket
import time
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from numpy import inf
from torch.utils.tensorboard import SummaryWriter

from replay_buffer import ReplayBuffer
from velodyne_env import GazeboEnv


def evaluate(network, epoch, eval_episodes=10):
    avg_reward = 0.0
    collision_episodes = 0
    success_episodes = 0
    avg_episode_steps = 0.0
    avg_final_distance = 0.0
    for _ in range(eval_episodes):
        count = 0
        state = env.reset()
        done = False
        episode_collision = False
        episode_success = False
        while not done and count < 501:
            action = network.get_action(np.array(state))
            a_in = [(action[0] + 1) / 2, action[1]]
            state, reward, done, _ = env.step(a_in)
            avg_reward += reward
            count += 1
            step_info = env.last_step_info
            episode_collision = episode_collision or step_info["collision"]
            episode_success = episode_success or step_info["target"]
        collision_episodes += int(episode_collision)
        success_episodes += int(episode_success)
        avg_episode_steps += count
        if env.last_step_info["distance"] is not None:
            avg_final_distance += env.last_step_info["distance"]
    avg_reward /= eval_episodes
    avg_collision_rate = collision_episodes / eval_episodes
    avg_success_rate = success_episodes / eval_episodes
    avg_episode_steps /= eval_episodes
    avg_final_distance /= eval_episodes
    print("..............................................")
    print(
        "Eval Epoch %i | avg_reward=%.3f | success_rate=%.3f | collision_rate=%.3f | "
        "avg_steps=%.1f | avg_final_distance=%.3f"
        % (
            epoch,
            avg_reward,
            avg_success_rate,
            avg_collision_rate,
            avg_episode_steps,
            avg_final_distance,
        )
    )
    print("..............................................")
    return {
        "avg_reward": avg_reward,
        "success_rate": avg_success_rate,
        "collision_rate": avg_collision_rate,
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
    def __init__(self, state_dim, action_dim, max_action, log_dir=None):
        self.actor = Actor(state_dim, action_dim).to(device)
        self.actor_target = Actor(state_dim, action_dim).to(device)
        self.actor_target.load_state_dict(self.actor.state_dict())
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters())

        self.critic = Critic(state_dim, action_dim).to(device)
        self.critic_target = Critic(state_dim, action_dim).to(device)
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

    def save(self, filename, directory):
        torch.save(self.actor.state_dict(), "%s/%s_actor.pth" % (directory, filename))
        torch.save(self.critic.state_dict(), "%s/%s_critic.pth" % (directory, filename))

    def load(self, filename, directory):
        self.actor.load_state_dict(
            torch.load("%s/%s_actor.pth" % (directory, filename))
        )
        self.critic.load_state_dict(
            torch.load("%s/%s_critic.pth" % (directory, filename))
        )

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
seed = 0
eval_freq = 5e3
max_ep = 500
eval_ep = 10
max_timesteps = 5e6
expl_noise = 1
expl_decay_steps = 500000
expl_min = 0.1
batch_size = 40
discount = 0.99999
tau = 0.005
policy_noise = 0.2
noise_clip = 0.5
policy_freq = 2
buffer_size = 1e6
file_name = "TD3_velodyne"
save_model = True
load_model = False
random_near_obstacle = True
resume_training = True
launchfile = os.environ.get("DRL_TRAIN_LAUNCHFILE", "multi_robot_scenario.launch")
checkpoint_dir = "./checkpoints"
checkpoint_path = os.path.join(checkpoint_dir, f"{file_name}_latest.pt")
checkpoint_interval_episodes = 10
training_version = "single-agent-v2-progress-reward"

if not os.path.exists("./results"):
    os.makedirs("./results")
if save_model and not os.path.exists("./pytorch_models"):
    os.makedirs("./pytorch_models")
if not os.path.exists(checkpoint_dir):
    os.makedirs(checkpoint_dir)


def make_run_log_dir():
    timestamp = datetime.now().strftime("%b%d_%H-%M-%S")
    return os.path.join("runs", f"{timestamp}_{socket.gethostname()}")


def save_training_checkpoint(
    network,
    replay_buffer,
    evaluations,
    timestep,
    timesteps_since_eval,
    episode_num,
    epoch,
    expl_noise_value,
):
    torch.save(
        {
            "network": network.state_dict(),
            "replay_buffer": replay_buffer.state_dict(),
            "evaluations": evaluations,
            "timestep": timestep,
            "timesteps_since_eval": timesteps_since_eval,
            "episode_num": episode_num,
            "epoch": epoch,
            "expl_noise": expl_noise_value,
        },
        checkpoint_path,
    )


def load_training_checkpoint():
    if not (resume_training and os.path.exists(checkpoint_path)):
        return None
    return torch.load(checkpoint_path, map_location="cpu")


environment_dim = 20
robot_dim = 4
env = GazeboEnv(launchfile, environment_dim)
time.sleep(5)
torch.manual_seed(seed)
np.random.seed(seed)
state_dim = environment_dim + robot_dim
action_dim = 2
max_action = 1

checkpoint = load_training_checkpoint()
log_dir = checkpoint["network"]["log_dir"] if checkpoint else make_run_log_dir()

network = TD3(state_dim, action_dim, max_action, log_dir=log_dir)
replay_buffer = ReplayBuffer(buffer_size, seed)

if checkpoint:
    network.load_state_dict(checkpoint["network"])
    replay_buffer.load_state_dict(checkpoint["replay_buffer"])
    print("Resumed training from checkpoint:", checkpoint_path)
elif load_model:
    try:
        network.load(file_name, "./pytorch_models")
    except Exception:
        print(
            "Could not load the stored model parameters, initializing training with random parameters"
        )

evaluations = checkpoint["evaluations"] if checkpoint else []
timestep = checkpoint["timestep"] if checkpoint else 0
timesteps_since_eval = checkpoint["timesteps_since_eval"] if checkpoint else 0
episode_num = checkpoint["episode_num"] if checkpoint else 0
done = True
epoch = checkpoint["epoch"] if checkpoint else 1
count_rand_actions = 0
random_action = []
expl_noise = checkpoint["expl_noise"] if checkpoint else expl_noise
train_start_time = time.time()

print("==============================================")
print("Training version:", training_version)
print("Training process PID:", os.getpid())
print("Launchfile:", launchfile)
print("Device:", device)
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
print("TensorBoard log dir:", log_dir)
print("Checkpoint path:", checkpoint_path)
print("Resume mode:", resume_training)
print("Starting timestep:", timestep)
print("Starting epoch:", epoch)
print("==============================================")

last_eval_summary = None

while timestep < max_timesteps:
    if done:
        if timestep != 0:
            network.train(
                replay_buffer,
                episode_timesteps,
                batch_size,
                discount,
                tau,
                policy_noise,
                noise_clip,
                policy_freq,
            )
            elapsed = time.time() - train_start_time
            steps_per_sec = timestep / elapsed if elapsed > 0 else 0.0
            step_info = env.last_step_info
            collision_flag = int(bool(step_info["collision"]))
            target_flag = int(bool(step_info["target"]))
            final_distance = (
                step_info["distance"] if step_info["distance"] is not None else float("nan")
            )
            progress = step_info["progress"]
            min_laser = (
                step_info["min_laser"] if step_info["min_laser"] is not None else float("nan")
            )
            print(
                "Episode %i complete | global_step=%i | episode_steps=%i | reward=%.3f | "
                "target=%i | collision=%i | final_distance=%.3f | progress=%.4f | "
                "min_laser=%.3f | expl_noise=%.4f | replay=%i | steps/sec=%.3f"
                % (
                    episode_num,
                    timestep,
                    episode_timesteps,
                    episode_reward,
                    target_flag,
                    collision_flag,
                    final_distance,
                    progress,
                    min_laser,
                    expl_noise,
                    replay_buffer.size(),
                    steps_per_sec,
                )
            )
            if episode_num % checkpoint_interval_episodes == 0:
                save_training_checkpoint(
                    network,
                    replay_buffer,
                    evaluations,
                    timestep,
                    timesteps_since_eval,
                    episode_num,
                    epoch,
                    expl_noise,
                )
                print("Checkpoint saved:", checkpoint_path)

        if timesteps_since_eval >= eval_freq:
            print("Validating at global_step=%i" % timestep)
            timesteps_since_eval %= eval_freq
            last_eval_summary = evaluate(network=network, epoch=epoch, eval_episodes=eval_ep)
            evaluations.append(
                [
                    last_eval_summary["avg_reward"],
                    last_eval_summary["success_rate"],
                    last_eval_summary["collision_rate"],
                    last_eval_summary["avg_episode_steps"],
                    last_eval_summary["avg_final_distance"],
                ]
            )
            network.save(file_name, directory="./pytorch_models")
            np.save("./results/%s" % (file_name), evaluations)
            save_training_checkpoint(
                network,
                replay_buffer,
                evaluations,
                timestep,
                timesteps_since_eval,
                episode_num,
                epoch,
                expl_noise,
            )
            print("Checkpoint saved:", checkpoint_path)
            epoch += 1

        state = env.reset()
        done = False
        episode_reward = 0
        episode_timesteps = 0
        episode_num += 1

    if expl_noise > expl_min:
        expl_noise = expl_noise - ((1 - expl_min) / expl_decay_steps)

    action = network.get_action(np.array(state))
    action = (action + np.random.normal(0, expl_noise, size=action_dim)).clip(
        -max_action, max_action
    )

    if random_near_obstacle:
        if (
            np.random.uniform(0, 1) > 0.85
            and min(state[:environment_dim]) < 0.6
            and count_rand_actions < 1
        ):
            count_rand_actions = np.random.randint(8, 15)
            random_action = np.random.uniform(-1, 1, 2)

        if count_rand_actions > 0:
            count_rand_actions -= 1
            action = random_action
            action[0] = -1

    a_in = [(action[0] + 1) / 2, action[1]]
    next_state, reward, done, target = env.step(a_in)
    done_bool = 0 if episode_timesteps + 1 == max_ep else int(done)
    done = 1 if episode_timesteps + 1 == max_ep else int(done)
    episode_reward += reward

    replay_buffer.add(state, action, reward, done_bool, next_state)

    state = next_state
    episode_timesteps += 1
    timestep += 1
    timesteps_since_eval += 1

last_eval_summary = evaluate(network=network, epoch=epoch, eval_episodes=eval_ep)
evaluations.append(
    [
        last_eval_summary["avg_reward"],
        last_eval_summary["success_rate"],
        last_eval_summary["collision_rate"],
        last_eval_summary["avg_episode_steps"],
        last_eval_summary["avg_final_distance"],
    ]
)
if save_model:
    network.save("%s" % file_name, directory="./pytorch_models")
np.save("./results/%s" % file_name, evaluations)
save_training_checkpoint(
    network,
    replay_buffer,
    evaluations,
    timestep,
    timesteps_since_eval,
    episode_num,
    epoch,
    expl_noise,
)
