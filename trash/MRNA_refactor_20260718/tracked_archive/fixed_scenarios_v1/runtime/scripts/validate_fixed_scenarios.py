#!/usr/bin/env python3
import argparse
import copy
import gzip
import json
import os
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "TD3"))

from scenario_manifests import load_manifest_dataset, validate_manifest_scenarios


def parse_args():
    parser = argparse.ArgumentParser(
        description="Filter a fixed scenario split using policy-independent Gazebo reset checks."
    )
    parser.add_argument("--input", required=True, help="Candidate split JSON")
    parser.add_argument("--accepted", required=True, help="Filtered split JSON")
    parser.add_argument("--rejected", required=True, help="Rejected scenario report JSON")
    parser.add_argument(
        "--launchfile", default="multi_robot_scenario_dense5_random_5d_5.launch"
    )
    parser.add_argument("--environment-dim", type=int, default=20)
    parser.add_argument("--collision-distance", type=float, default=0.35)
    parser.add_argument("--position-tolerance", type=float, default=0.15)
    parser.add_argument(
        "--target-count",
        type=int,
        default=0,
        help="Keep at most this many valid scenarios after checking all candidates",
    )
    return parser.parse_args()


def write_json(path, payload):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".gz":
        handle_context = gzip.open(output, "wt", encoding="utf-8")
    else:
        handle_context = output.open("w", encoding="utf-8")
    with handle_context as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def validate_reset(env, scenario, collision_distance, position_tolerance):
    env.reset()
    selected_id = str(env.current_curriculum_case.get("scenario_id", ""))
    if selected_id != scenario["scenario_id"]:
        return False, {"reason": "manifest_cycle_mismatch", "selected_id": selected_id}

    zero_actions = [[0.0, 0.0] for _ in env.agent_names]
    _, _, dones, targets, collisions = env.step(zero_actions)
    measurements = {}
    reasons = []
    for index, name in enumerate(env.agent_names):
        odom = env.last_odom.get(name)
        laser = np.asarray(env.velodyne_data.get(name), dtype=float)
        if odom is None:
            reasons.append(f"{name}:missing_odom")
            continue
        observed = np.array(
            [odom.pose.pose.position.x, odom.pose.pose.position.y], dtype=float
        )
        expected = np.asarray(scenario["agents"][name]["start"], dtype=float)
        position_error = float(np.linalg.norm(observed - expected))
        min_laser = float(np.min(laser)) if laser.size else float("nan")
        measurements[name] = {
            "position_error_m": position_error,
            "min_laser_m": min_laser,
        }
        if not np.all(np.isfinite(observed)):
            reasons.append(f"{name}:nonfinite_odom")
        if laser.size != env.environment_dim or not np.all(np.isfinite(laser)):
            reasons.append(f"{name}:invalid_laser")
        elif min_laser < collision_distance:
            reasons.append(f"{name}:initial_clearance")
        if position_error > position_tolerance:
            reasons.append(f"{name}:reset_position_error")
        if bool(collisions[index]):
            reasons.append(f"{name}:initial_collision")
        if bool(dones[index]) or bool(targets[index]):
            reasons.append(f"{name}:initial_terminal")

    details = {
        "reason": reasons[0] if reasons else None,
        "all_reasons": reasons,
        "measurements": measurements,
    }
    return not reasons, details


def main():
    args = parse_args()
    input_path = str(Path(args.input).resolve())
    payload = load_manifest_dataset(input_path)
    agent_names = [f"r{index}" for index in range(1, 6)]
    scenarios = validate_manifest_scenarios(payload["scenarios"], agent_names)

    os.environ["DRL_MULTI_SCENARIO"] = "manifest"
    os.environ["DRL_MULTI_MANIFEST_PATH"] = input_path
    os.environ["DRL_MULTI_MANIFEST_SAMPLING"] = "cycle"
    from multi_agent_velodyne_env import MultiAgentGazeboEnv

    env = MultiAgentGazeboEnv(
        args.launchfile,
        args.environment_dim,
        agent_names=agent_names,
        cooperative_reward=False,
        robot_safe_distance=0.0,
        weak_coupling_layout=True,
        scenario_mode="manifest",
    )

    accepted = []
    rejected = []
    try:
        for index, scenario in enumerate(scenarios, start=1):
            valid, details = validate_reset(
                env, scenario, args.collision_distance, args.position_tolerance
            )
            if valid:
                item = copy.deepcopy(scenario)
                item.pop("layout", None)
                if item.get("name") == item.get("scenario_id"):
                    item.pop("name", None)
                item["validity"]["gazebo_reset"] = True
                item["validity"]["gazebo_reset_details"] = details["measurements"]
                accepted.append(item)
            else:
                rejected.append(
                    {
                        "scenario_id": scenario["scenario_id"],
                        "generation_seed": scenario.get("generation_seed"),
                        **details,
                    }
                )
            print(
                "[%i/%i] %s: %s"
                % (
                    index,
                    len(scenarios),
                    scenario["scenario_id"],
                    "accepted" if valid else details["reason"],
                ),
                flush=True,
            )
    finally:
        env.close()

    valid_count = len(accepted)
    if args.target_count:
        accepted = accepted[: args.target_count]
    accepted_payload = copy.deepcopy(payload)
    accepted_payload["scenarios"] = accepted
    accepted_payload["gazebo_validation"] = {
        "policy_independent": True,
        "candidate_count": len(scenarios),
        "accepted_count": len(accepted),
        "valid_candidate_count": valid_count,
        "rejected_count": len(rejected),
        "collision_distance_m": args.collision_distance,
        "position_tolerance_m": args.position_tolerance,
    }
    rejected_payload = {
        "dataset_id": payload.get("dataset_id"),
        "split": payload.get("split"),
        "candidate_count": len(scenarios),
        "rejected_count": len(rejected),
        "rejected": rejected,
    }
    write_json(args.accepted, accepted_payload)
    write_json(args.rejected, rejected_payload)
    print(
        "Kept %i scenarios from %i valid candidates; rejected %i/%i"
        % (len(accepted), valid_count, len(rejected), len(scenarios))
    )
    if args.target_count and valid_count < args.target_count:
        raise RuntimeError(
            "Only %i valid scenarios were available, but target-count is %i"
            % (valid_count, args.target_count)
        )


if __name__ == "__main__":
    main()
