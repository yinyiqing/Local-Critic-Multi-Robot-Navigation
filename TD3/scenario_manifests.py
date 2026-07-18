import gzip
import json
import math
import os
from pathlib import Path

from scenario_geometry import is_valid_map_position


MANIFEST_GROUPS = ("standard", "dense")


def parse_manifest_paths(value, base_dir=None):
    """Parse an os.pathsep-delimited path list and return absolute paths."""
    if isinstance(value, (str, os.PathLike)):
        entries = str(value).split(os.pathsep)
    else:
        entries = list(value)
    root = Path(base_dir or os.getcwd())
    paths = []
    for entry in entries:
        entry = str(entry).strip()
        if not entry:
            continue
        candidate = Path(entry).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        paths.append(candidate.resolve())
    if not paths:
        raise ValueError("At least one manifest path is required")
    return paths


def load_manifest_dataset(path):
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest dataset does not exist: {manifest_path}")
    if manifest_path.suffix == ".gz":
        handle_context = gzip.open(manifest_path, "rt", encoding="utf-8")
    else:
        handle_context = manifest_path.open("r", encoding="utf-8")
    with handle_context as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("scenarios"), list):
        raise ValueError(f"Manifest dataset must contain a scenarios list: {manifest_path}")
    if not payload["scenarios"]:
        raise ValueError(f"Manifest dataset must contain at least one scenario: {manifest_path}")
    return payload


def _validate_position(value, label, scenario_id):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(
            f"Manifest scenario {scenario_id} {label} must contain [x, y]"
        )
    position = [float(item) for item in value]
    if not all(math.isfinite(item) for item in position):
        raise ValueError(f"Manifest scenario {scenario_id} {label} must be finite")
    if not is_valid_map_position(*position):
        raise ValueError(
            f"Manifest scenario {scenario_id} {label} is outside free map space"
        )


def validate_manifest_scenarios(scenarios, agent_names):
    """Validate and normalize fixed scenarios without importing ROS."""
    expected_agents = set(agent_names)
    normalized = []
    scenario_ids = set()
    for index, source in enumerate(scenarios):
        if not isinstance(source, dict):
            raise ValueError(f"Manifest scenario {index} must be an object")
        scenario = dict(source)
        scenario_id = str(scenario.get("scenario_id", "")).strip()
        if not scenario_id:
            raise ValueError(f"Manifest scenario {index} is missing scenario_id")
        if scenario_id in scenario_ids:
            raise ValueError(f"Duplicate manifest scenario_id: {scenario_id}")
        scenario_ids.add(scenario_id)

        if int(scenario.get("manifest_version", 0)) != 1:
            raise ValueError(
                f"Manifest scenario {scenario_id} has an unsupported manifest_version"
            )
        if str(scenario.get("map_id", "")) != "TD3.world-v1":
            raise ValueError(
                f"Manifest scenario {scenario_id} does not target TD3.world-v1"
            )
        preset = str(scenario.get("preset", "")).strip().lower()
        if preset not in MANIFEST_GROUPS:
            raise ValueError(
                f"Manifest scenario {scenario_id} preset must be standard or dense"
            )

        agents = scenario.get("agents")
        if not isinstance(agents, dict) or set(agents) != expected_agents:
            raise ValueError(
                f"Manifest scenario {scenario_id} agents must exactly match "
                f"{sorted(expected_agents)}"
            )
        if int(scenario.get("num_agents", -1)) != len(agent_names):
            raise ValueError(
                f"Manifest scenario {scenario_id} num_agents does not match the environment"
            )
        for name in agent_names:
            agent = agents[name]
            if not isinstance(agent, dict):
                raise ValueError(f"Manifest scenario {scenario_id} {name} must be an object")
            _validate_position(agent.get("start"), f"{name}.start", scenario_id)
            _validate_position(agent.get("goal"), f"{name}.goal", scenario_id)
            heading = agent.get("heading")
            if heading is None or not math.isfinite(float(heading)):
                raise ValueError(
                    f"Manifest scenario {scenario_id} {name}.heading must be finite"
                )

        boxes = scenario.get("boxes")
        if not isinstance(boxes, list) or len(boxes) > 4:
            raise ValueError(
                f"Manifest scenario {scenario_id} boxes must contain at most 4 positions"
            )
        for box_index, box in enumerate(boxes):
            _validate_position(box, f"boxes[{box_index}]", scenario_id)

        scenario["name"] = scenario_id
        scenario["group"] = preset
        scenario["layout"] = "fixed"
        normalized.append(scenario)
    return normalized


def load_manifest_cases(paths, agent_names, group_ratios=None, base_dir=None):
    """Load several splits, validate global IDs, and assign group-balanced weights."""
    manifest_paths = parse_manifest_paths(paths, base_dir=base_dir)
    scenarios = []
    metadata = []
    for manifest_path in manifest_paths:
        payload = load_manifest_dataset(manifest_path)
        dataset_id = str(payload.get("dataset_id", "")).strip()
        if not dataset_id:
            raise ValueError(f"Manifest dataset is missing dataset_id: {manifest_path}")
        split = str(payload.get("split", "")).strip()
        metadata.append({"dataset_id": dataset_id, "split": split, "path": str(manifest_path)})
        for source in payload["scenarios"]:
            scenario = dict(source)
            scenario["dataset_id"] = dataset_id
            scenarios.append(scenario)

    cases = validate_manifest_scenarios(scenarios, agent_names)
    counts = {
        group: sum(case["group"] == group for case in cases)
        for group in MANIFEST_GROUPS
    }
    ratios = {group: 1.0 for group in MANIFEST_GROUPS}
    if group_ratios is not None:
        unknown = set(group_ratios) - set(MANIFEST_GROUPS)
        if unknown:
            raise ValueError(f"Unsupported manifest groups: {sorted(unknown)}")
        ratios.update({group: float(value) for group, value in group_ratios.items()})
    if any(value < 0.0 for value in ratios.values()) or sum(ratios.values()) <= 0.0:
        raise ValueError("Manifest group ratios must be non-negative with a positive sum")
    for group, ratio in ratios.items():
        if ratio > 0.0 and counts[group] == 0:
            raise ValueError(f"No manifest scenarios found for enabled group: {group}")
    for case in cases:
        count = counts[case["group"]]
        case["weight"] = ratios[case["group"]] / count if count else 0.0
    return cases, metadata
