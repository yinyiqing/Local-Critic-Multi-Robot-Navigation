#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "TD3"))

from scenario_manifests import (
    AGENT_NAMES,
    load_manifest_dataset,
    validate_manifest_scenarios,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Audit fixed scenario manifests for replay and split integrity."
    )
    parser.add_argument("manifests", nargs="+", help="JSON or JSON.GZ split files")
    return parser.parse_args()


def main():
    args = parse_args()
    all_ids = set()
    summaries = []
    for source in args.manifests:
        path = Path(source)
        payload = load_manifest_dataset(path)
        scenarios = validate_manifest_scenarios(payload["scenarios"], AGENT_NAMES)
        expected_split = str(payload.get("split", ""))
        ids = []
        for scenario in scenarios:
            scenario_id = scenario["scenario_id"]
            if scenario_id in all_ids:
                raise ValueError(f"Scenario ID appears in multiple splits: {scenario_id}")
            all_ids.add(scenario_id)
            ids.append(scenario_id)
            if scenario.get("split") != expected_split:
                raise ValueError(
                    f"{scenario_id} split is {scenario.get('split')}, expected {expected_split}"
                )
            if scenario.get("validity", {}).get("gazebo_reset") is not True:
                raise ValueError(f"{scenario_id} has not passed Gazebo reset validation")

        edge_counts = [item["metrics"]["conflict_edge_count"] for item in scenarios]
        task_mins = [item["validity"]["min_task_distance_m"] for item in scenarios]
        task_maxes = [item["validity"]["max_task_distance_m"] for item in scenarios]
        summaries.append(
            {
                "path": str(path),
                "dataset_id": payload.get("dataset_id"),
                "split": expected_split,
                "scenarios": len(ids),
                "conflict_edges_mean": sum(edge_counts) / len(edge_counts),
                "conflict_edges_min": min(edge_counts),
                "conflict_edges_max": max(edge_counts),
                "task_distance_min_m": min(task_mins),
                "task_distance_max_m": max(task_maxes),
            }
        )
    print(json.dumps({"total_scenarios": len(all_ids), "splits": summaries}, indent=2))


if __name__ == "__main__":
    main()
