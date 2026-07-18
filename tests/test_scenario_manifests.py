import gzip
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TD3"))

from scenario_geometry import has_map_clearance, is_valid_map_position
from scenario_manifests import load_manifest_cases, parse_manifest_paths


AGENT_NAMES = [f"r{index}" for index in range(1, 6)]


def make_scenario(scenario_id, preset, offset=0.0):
    agents = {}
    for index, name in enumerate(AGENT_NAMES):
        angle = 2.0 * math.pi * index / len(AGENT_NAMES)
        start = [
            round(offset + 0.5 * math.cos(angle), 6),
            round(0.5 * math.sin(angle), 6),
        ]
        goal = [
            round(offset + 0.8 * math.cos(angle), 6),
            round(0.8 * math.sin(angle), 6),
        ]
        agents[name] = {"start": start, "goal": goal, "heading": angle}
    return {
        "manifest_version": 1,
        "scenario_id": scenario_id,
        "preset": preset,
        "map_id": "TD3.world-v1",
        "num_agents": 5,
        "agents": agents,
        "boxes": [],
    }


def write_manifest(directory, name, dataset_id, split, scenarios):
    path = Path(directory) / name
    payload = {
        "dataset_version": 1,
        "dataset_id": dataset_id,
        "split": split,
        "scenarios": scenarios,
    }
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return path


class ScenarioGeometryTests(unittest.TestCase):
    def test_geometry_matches_known_map_regions(self):
        self.assertTrue(is_valid_map_position(0.0, 0.0))
        self.assertFalse(is_valid_map_position(-2.0, 0.0))
        self.assertFalse(has_map_clearance((4.4, 0.0), 0.24))


class ManifestIntegrationTests(unittest.TestCase):
    def test_loads_multiple_files_and_balances_group_probability(self):
        with tempfile.TemporaryDirectory() as directory:
            standard_path = write_manifest(
                directory,
                "standard.json.gz",
                "standard-train",
                "train",
                [make_scenario("standard-1", "standard")],
            )
            dense_path = write_manifest(
                directory,
                "dense.json.gz",
                "dense-train",
                "train",
                [
                    make_scenario("dense-1", "dense", 0.1),
                    make_scenario("dense-2", "dense", 0.2),
                ],
            )
            cases, metadata = load_manifest_cases(
                os.pathsep.join([str(standard_path), str(dense_path)]),
                AGENT_NAMES,
            )

        self.assertEqual([item["dataset_id"] for item in metadata], ["standard-train", "dense-train"])
        self.assertEqual({case["group"] for case in cases}, {"standard", "dense"})
        self.assertTrue(all(case["layout"] == "fixed" for case in cases))
        self.assertTrue(all(case["name"] == case["scenario_id"] for case in cases))
        standard_weight = sum(
            case["weight"] for case in cases if case["group"] == "standard"
        )
        dense_weight = sum(
            case["weight"] for case in cases if case["group"] == "dense"
        )
        self.assertAlmostEqual(standard_weight, dense_weight)

    def test_rejects_duplicate_ids_across_files(self):
        with tempfile.TemporaryDirectory() as directory:
            first = write_manifest(
                directory,
                "first.json.gz",
                "standard-train",
                "train",
                [make_scenario("duplicate", "standard")],
            )
            second = write_manifest(
                directory,
                "second.json.gz",
                "dense-train",
                "train",
                [make_scenario("duplicate", "dense")],
            )
            with self.assertRaisesRegex(ValueError, "Duplicate manifest scenario_id"):
                load_manifest_cases([first, second], AGENT_NAMES)

    def test_rejects_agent_name_mismatch(self):
        scenario = make_scenario("broken-agents", "standard")
        scenario["agents"]["robot5"] = scenario["agents"].pop("r5")
        with tempfile.TemporaryDirectory() as directory:
            path = write_manifest(
                directory,
                "broken.json.gz",
                "standard-train",
                "train",
                [scenario],
            )
            with self.assertRaisesRegex(ValueError, "agents must exactly match"):
                load_manifest_cases([path], AGENT_NAMES)

    def test_path_list_supports_relative_entries(self):
        paths = parse_manifest_paths(
            os.pathsep.join(["standard/train.json.gz", "dense/train.json.gz"]),
            base_dir="/tmp/fixed_v1",
        )
        self.assertEqual(
            paths,
            [
                Path("/tmp/fixed_v1/standard/train.json.gz"),
                Path("/tmp/fixed_v1/dense/train.json.gz"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
