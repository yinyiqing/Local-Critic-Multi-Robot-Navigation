#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "TD3"))

from scenario_manifests import PRESETS, generate_dataset, write_dataset_splits


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate policy-independent fixed random scenario manifests."
    )
    parser.add_argument("--preset", choices=sorted(PRESETS), required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--train", type=int, default=0)
    parser.add_argument("--validation", type=int, default=0)
    parser.add_argument("--test", type=int, default=0)
    parser.add_argument("--reserve", type=int, default=0)
    parser.add_argument("--max-candidates", type=int)
    return parser.parse_args()


def summarize(datasets):
    summary = {}
    for split, payload in datasets.items():
        scenarios = payload["scenarios"]
        if not scenarios:
            continue
        edge_counts = [item["metrics"]["conflict_edge_count"] for item in scenarios]
        task_mins = [item["validity"]["min_task_distance_m"] for item in scenarios]
        task_maxes = [item["validity"]["max_task_distance_m"] for item in scenarios]
        summary[split] = {
            "scenarios": len(scenarios),
            "conflict_edges_min": min(edge_counts),
            "conflict_edges_max": max(edge_counts),
            "conflict_edges_mean": sum(edge_counts) / len(edge_counts),
            "task_distance_min_m": min(task_mins),
            "task_distance_max_m": max(task_maxes),
        }
    return summary


def main():
    args = parse_args()
    split_sizes = {
        "train": args.train,
        "validation": args.validation,
        "test": args.test,
        "reserve": args.reserve,
    }
    datasets = generate_dataset(
        PRESETS[args.preset],
        split_sizes,
        master_seed=args.seed,
        max_candidates=args.max_candidates,
    )
    written = write_dataset_splits(datasets, args.output_dir)
    print(json.dumps(summarize(datasets), indent=2, sort_keys=True))
    for path in written:
        print("Wrote", path)


if __name__ == "__main__":
    main()
