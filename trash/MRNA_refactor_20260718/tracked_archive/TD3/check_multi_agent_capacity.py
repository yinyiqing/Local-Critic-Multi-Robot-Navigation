#!/usr/bin/env python3
import argparse
import os
import time

import numpy as np

from multi_agent_velodyne_env import MultiAgentGazeboEnv


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check Gazebo capacity for multi-agent robot navigation."
    )
    parser.add_argument("--num-agents", type=int, default=2)
    parser.add_argument("--launchfile", required=True)
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--environment-dim", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--weak-coupling-layout", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    np.random.seed(args.seed)

    agent_names = [f"r{i}" for i in range(1, args.num_agents + 1)]
    print("==============================================")
    print("Multi-agent capacity check")
    print("PID:", os.getpid())
    print("Launchfile:", args.launchfile)
    print("Agent names:", ", ".join(agent_names))
    print("Episodes:", args.episodes)
    print("Steps per episode:", args.steps)
    print("Weak coupling layout:", args.weak_coupling_layout)
    print("==============================================")

    env = MultiAgentGazeboEnv(
        args.launchfile,
        args.environment_dim,
        agent_names=agent_names,
        cooperative_reward=False,
        robot_safe_distance=0.0,
        weak_coupling_layout=args.weak_coupling_layout,
    )
    time.sleep(5)

    total_resets = 0
    total_env_steps = 0
    total_targets = 0
    total_collisions = 0
    total_timeouts = 0
    reset_failures = 0
    min_lasers = []
    nearest_robot_distances = []
    final_distances = []
    start_time = time.time()

    for episode in range(1, args.episodes + 1):
        try:
            states = env.reset()
        except Exception as exc:
            reset_failures += 1
            print(f"Episode {episode} reset failed: {exc}")
            continue

        total_resets += 1
        active_mask = [True] * args.num_agents
        episode_targets = np.zeros(args.num_agents, dtype=np.int32)
        episode_collisions = np.zeros(args.num_agents, dtype=np.int32)

        for step in range(1, args.steps + 1):
            actions = []
            for active in active_mask:
                if active:
                    linear = np.random.uniform(0.0, 0.6)
                    angular = np.random.uniform(-0.8, 0.8)
                    actions.append([linear, angular])
                else:
                    actions.append([0.0, 0.0])

            states, rewards, dones, targets, collisions = env.step(actions, active_mask)
            total_env_steps += 1

            step_info = env.last_step_info["agents"]
            for idx, name in enumerate(agent_names):
                info = step_info[name]
                if info["min_laser"] is not None:
                    min_lasers.append(float(info["min_laser"]))
                if info["nearest_robot_distance"] is not None:
                    nearest_robot_distances.append(float(info["nearest_robot_distance"]))
                if info["distance"] is not None:
                    final_distances.append(float(info["distance"]))
                episode_targets[idx] = max(episode_targets[idx], int(targets[idx]))
                episode_collisions[idx] = max(
                    episode_collisions[idx], int(collisions[idx])
                )
                if active_mask[idx] and dones[idx]:
                    active_mask[idx] = False

            if not any(active_mask):
                break

        episode_timeouts = int(sum(1 for active in active_mask if active))
        total_targets += int(np.sum(episode_targets))
        total_collisions += int(np.sum(episode_collisions))
        total_timeouts += episode_timeouts

        nearest_mean = (
            float(np.mean(nearest_robot_distances[-args.num_agents :]))
            if nearest_robot_distances
            else float("nan")
        )
        min_laser_recent = float(np.min(min_lasers[-args.num_agents :])) if min_lasers else float("nan")
        print(
            "Capacity episode %i/%i | steps=%i | success=%i/%i | collision=%i/%i | "
            "timeout=%i/%i | recent_min_laser=%.3f | recent_robot_dist=%.3f"
            % (
                episode,
                args.episodes,
                step,
                int(np.sum(episode_targets)),
                args.num_agents,
                int(np.sum(episode_collisions)),
                args.num_agents,
                episode_timeouts,
                args.num_agents,
                min_laser_recent,
                nearest_mean,
            )
        )

    elapsed = time.time() - start_time
    total_agent_trials = max(total_resets * args.num_agents, 1)
    print("==============================================")
    print("Capacity check summary")
    print("num_agents:", args.num_agents)
    print("successful_resets:", total_resets)
    print("reset_failures:", reset_failures)
    print("env_steps:", total_env_steps)
    print("env_steps_per_sec: %.3f" % (total_env_steps / elapsed if elapsed > 0 else 0.0))
    print("success_rate: %.3f" % (total_targets / total_agent_trials))
    print("collision_rate: %.3f" % (total_collisions / total_agent_trials))
    print("timeout_rate: %.3f" % (total_timeouts / total_agent_trials))
    if min_lasers:
        print("min_laser_min: %.3f" % float(np.min(min_lasers)))
        print("min_laser_mean: %.3f" % float(np.mean(min_lasers)))
    if nearest_robot_distances:
        print("nearest_robot_distance_min: %.3f" % float(np.min(nearest_robot_distances)))
        print(
            "nearest_robot_distance_mean: %.3f"
            % float(np.mean(nearest_robot_distances))
        )
    if final_distances:
        print("avg_observed_goal_distance: %.3f" % float(np.mean(final_distances)))
    print("==============================================")


if __name__ == "__main__":
    main()
