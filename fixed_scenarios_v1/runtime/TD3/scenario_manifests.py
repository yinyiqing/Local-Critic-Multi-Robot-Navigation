import gzip
import hashlib
import heapq
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from scenario_geometry import MAP_LIMIT, has_map_clearance


AGENT_NAMES = ("r1", "r2", "r3", "r4", "r5")
SPLIT_NAMES = ("train", "validation", "test", "reserve")


@dataclass(frozen=True)
class ScenarioConfig:
    preset: str
    start_half_width_min: float
    start_half_width_max: float
    robot_clearance: float
    goal_min_distance: float
    goal_max_distance: float
    goal_clearance: float
    robot_goal_clearance: float
    box_clearance: float
    box_box_clearance: float = 0.8
    num_boxes: int = 4
    robot_map_clearance: float = 0.24
    box_map_clearance: float = 0.35
    planner_resolution: float = 0.15
    nominal_speed: float = 0.5
    conflict_distance: float = 0.9
    conflict_horizon: float = 8.0


PRESETS = {
    "standard": ScenarioConfig(
        preset="standard",
        start_half_width_min=4.5,
        start_half_width_max=4.5,
        robot_clearance=0.95,
        goal_min_distance=0.8,
        goal_max_distance=3.5,
        goal_clearance=0.85,
        robot_goal_clearance=0.75,
        box_clearance=1.0,
    ),
    "dense": ScenarioConfig(
        preset="dense",
        start_half_width_min=1.65,
        start_half_width_max=1.75,
        robot_clearance=1.2,
        goal_min_distance=0.9,
        goal_max_distance=2.3,
        goal_clearance=0.8,
        robot_goal_clearance=0.8,
        box_clearance=2.0,
    ),
}

_PLANNER_CACHE = {}


def pairwise_min_distance(points):
    values = list(points)
    if len(values) < 2:
        return float("inf")
    return min(
        math.dist(values[left], values[right])
        for left in range(len(values))
        for right in range(left + 1, len(values))
    )


def _far_enough(candidate, existing, clearance):
    return all(math.dist(candidate, point) >= clearance for point in existing)


class GridPlanner:
    def __init__(self, resolution, map_clearance):
        self.resolution = float(resolution)
        self.map_clearance = float(map_clearance)
        self.axis = np.arange(-MAP_LIMIT, MAP_LIMIT + resolution * 0.5, resolution)
        self.shape = (len(self.axis), len(self.axis))
        self.static_valid = np.zeros(self.shape, dtype=bool)
        for x_index, x in enumerate(self.axis):
            for y_index, y in enumerate(self.axis):
                self.static_valid[x_index, y_index] = has_map_clearance(
                    (x, y), self.map_clearance
                )

    def _index(self, point):
        index = np.rint((np.asarray(point) + MAP_LIMIT) / self.resolution).astype(int)
        return tuple(np.clip(index, 0, len(self.axis) - 1))

    def _point(self, index):
        return (float(self.axis[index[0]]), float(self.axis[index[1]]))

    def _valid_grid(self, boxes):
        valid = self.static_valid.copy()
        box_radius = math.hypot(0.25, 0.20) + self.map_clearance
        if boxes:
            x_grid, y_grid = np.meshgrid(self.axis, self.axis, indexing="ij")
            for box in boxes:
                valid &= (x_grid - box[0]) ** 2 + (y_grid - box[1]) ** 2 >= box_radius**2
        return valid

    @staticmethod
    def _neighbors(index, shape):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                candidate = (index[0] + dx, index[1] + dy)
                if 0 <= candidate[0] < shape[0] and 0 <= candidate[1] < shape[1]:
                    yield candidate, math.hypot(dx, dy)

    def plan(self, start, goal, boxes):
        valid = self._valid_grid(boxes)
        start_index = self._index(start)
        goal_index = self._index(goal)
        if not valid[start_index] or not valid[goal_index]:
            return None

        frontier = [(0.0, start_index)]
        costs = {start_index: 0.0}
        parents = {}
        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal_index:
                break
            current_cost = costs[current]
            for neighbor, step_cost in self._neighbors(current, self.shape):
                if not valid[neighbor]:
                    continue
                candidate_cost = current_cost + step_cost
                if candidate_cost >= costs.get(neighbor, float("inf")):
                    continue
                costs[neighbor] = candidate_cost
                parents[neighbor] = current
                heuristic = math.dist(neighbor, goal_index)
                heapq.heappush(frontier, (candidate_cost + heuristic, neighbor))
        if goal_index not in costs:
            return None

        indices = [goal_index]
        while indices[-1] != start_index:
            indices.append(parents[indices[-1]])
        indices.reverse()
        points = [tuple(map(float, start))]
        points.extend(self._point(index) for index in indices[1:-1])
        points.append(tuple(map(float, goal)))
        return _simplify_path(points)


def _simplify_path(points):
    if len(points) <= 2:
        return points
    result = [points[0]]
    previous_direction = None
    for index in range(1, len(points)):
        dx = round(points[index][0] - points[index - 1][0], 6)
        dy = round(points[index][1] - points[index - 1][1], 6)
        norm = math.hypot(dx, dy)
        direction = (round(dx / norm, 4), round(dy / norm, 4)) if norm else (0.0, 0.0)
        if previous_direction is not None and direction != previous_direction:
            result.append(points[index - 1])
        previous_direction = direction
    result.append(points[-1])
    return result


def _path_lengths(path):
    segments = [math.dist(path[index - 1], path[index]) for index in range(1, len(path))]
    return segments, sum(segments)


def _position_on_path(path, distance):
    remaining = max(float(distance), 0.0)
    for index in range(1, len(path)):
        start = np.asarray(path[index - 1], dtype=float)
        end = np.asarray(path[index], dtype=float)
        length = float(np.linalg.norm(end - start))
        if length <= 1e-9:
            continue
        if remaining <= length:
            return start + (remaining / length) * (end - start)
        remaining -= length
    return np.asarray(path[-1], dtype=float)


def conflict_graph(paths, nominal_speed=0.5, conflict_distance=0.9, horizon=8.0):
    path_lengths = {name: _path_lengths(path)[1] for name, path in paths.items()}
    edges = []
    pair_min_distances = []
    names = sorted(paths)
    time_step = 0.1
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            active_horizon = min(
                horizon,
                max(
                    path_lengths[left] / nominal_speed,
                    path_lengths[right] / nominal_speed,
                ),
            )
            times = np.arange(0.0, active_horizon + time_step * 0.5, time_step)
            if len(times) == 0:
                continue
            distances = []
            for current_time in times:
                left_position = _position_on_path(
                    paths[left], nominal_speed * current_time
                )
                right_position = _position_on_path(
                    paths[right], nominal_speed * current_time
                )
                distances.append(float(np.linalg.norm(left_position - right_position)))
            min_index = int(np.argmin(distances))
            pair_min_distances.append(distances[min_index])
            if distances[min_index] < conflict_distance:
                edges.append(
                    {
                        "agents": [left, right],
                        "min_distance_m": round(distances[min_index], 6),
                        "time_s": round(float(times[min_index]), 3),
                    }
                )
    degrees = {name: 0 for name in names}
    for edge in edges:
        for name in edge["agents"]:
            degrees[name] += 1
    denominator = len(names) * (len(names) - 1)
    interaction_density = 2.0 * len(edges) / denominator if denominator else 0.0
    edge_times = [edge["time_s"] for edge in edges]
    simultaneous = 0
    for time_value in edge_times:
        simultaneous = max(
            simultaneous,
            sum(abs(other - time_value) <= 0.5 for other in edge_times),
        )
    return {
        "conflict_edges": edges,
        "conflict_edge_count": len(edges),
        "interaction_density": interaction_density,
        "max_conflict_degree": max(degrees.values(), default=0),
        "mean_conflict_degree": (
            sum(degrees.values()) / len(degrees) if degrees else 0.0
        ),
        "earliest_conflict_time_s": min(edge_times) if edge_times else None,
        "simultaneous_conflict_count": simultaneous,
        "min_synchronized_path_separation_m": (
            min(pair_min_distances) if pair_min_distances else None
        ),
    }


def _sample_point(rng, half_width, clearance):
    for _ in range(2000):
        point = rng.uniform(-half_width, half_width, size=2)
        if has_map_clearance(point, clearance):
            return tuple(map(float, point))
    raise RuntimeError("Could not sample a map-valid point")


def _sample_starts(rng, config, half_width):
    starts = []
    for _ in AGENT_NAMES:
        for _ in range(3000):
            candidate = _sample_point(rng, half_width, config.robot_map_clearance)
            if _far_enough(candidate, starts, config.robot_clearance):
                starts.append(candidate)
                break
        else:
            raise RuntimeError("Could not place all robot starts")
    return dict(zip(AGENT_NAMES, starts))


def _sample_dense_goal(rng, start, half_width, config):
    for _ in range(3000):
        distance = rng.uniform(config.goal_min_distance, config.goal_max_distance)
        angle = rng.uniform(-math.pi, math.pi)
        candidate = (
            start[0] + distance * math.cos(angle),
            start[1] + distance * math.sin(angle),
        )
        if not (-half_width <= candidate[0] <= half_width):
            continue
        if not (-half_width <= candidate[1] <= half_width):
            continue
        if has_map_clearance(candidate, config.robot_map_clearance):
            return candidate
    raise RuntimeError("Could not sample a dense goal")


def _sample_standard_goal(rng, start, half_width, config):
    for _ in range(3000):
        candidate = (
            float(np.clip(start[0] + rng.uniform(-2.2, 2.2), -half_width, half_width)),
            float(np.clip(start[1] + rng.uniform(-2.4, 2.4), -half_width, half_width)),
        )
        distance = math.dist(start, candidate)
        if not config.goal_min_distance <= distance <= config.goal_max_distance:
            continue
        if has_map_clearance(candidate, config.robot_map_clearance):
            return candidate
    raise RuntimeError("Could not sample a standard goal")


def _sample_goals(rng, starts, config, half_width):
    goals = {}
    for name in AGENT_NAMES:
        for _ in range(3000):
            candidate = (
                _sample_dense_goal(rng, starts[name], half_width, config)
                if config.preset == "dense"
                else _sample_standard_goal(rng, starts[name], half_width, config)
            )
            if not _far_enough(candidate, goals.values(), config.goal_clearance):
                continue
            if not _far_enough(candidate, starts.values(), config.robot_goal_clearance):
                continue
            goals[name] = candidate
            break
        else:
            raise RuntimeError("Could not place all goals")
    return goals


def _sample_boxes(rng, starts, goals, config):
    boxes = []
    protected = list(starts.values()) + list(goals.values())
    for _ in range(config.num_boxes):
        for _ in range(5000):
            candidate = tuple(map(float, rng.uniform(-6.0, 6.0, size=2)))
            if not has_map_clearance(candidate, config.box_map_clearance):
                continue
            if not _far_enough(candidate, protected, config.box_clearance):
                continue
            if not _far_enough(candidate, boxes, config.box_box_clearance):
                continue
            boxes.append(candidate)
            break
        else:
            raise RuntimeError("Could not place all boxes")
    return boxes


def generate_scenario(generation_seed, config):
    rng = np.random.default_rng(int(generation_seed))
    half_width = float(
        rng.uniform(config.start_half_width_min, config.start_half_width_max)
        if config.start_half_width_min != config.start_half_width_max
        else config.start_half_width_min
    )
    starts = _sample_starts(rng, config, half_width)
    goals = _sample_goals(rng, starts, config, half_width)
    boxes = _sample_boxes(rng, starts, goals, config)

    planner_key = (config.planner_resolution, config.robot_map_clearance)
    planner = _PLANNER_CACHE.get(planner_key)
    if planner is None:
        planner = GridPlanner(*planner_key)
        _PLANNER_CACHE[planner_key] = planner
    paths = {}
    for name in AGENT_NAMES:
        path = planner.plan(starts[name], goals[name], boxes)
        if path is None:
            raise RuntimeError(f"No static path for {name}")
        paths[name] = path

    conflict = conflict_graph(
        paths,
        nominal_speed=config.nominal_speed,
        conflict_distance=config.conflict_distance,
        horizon=config.conflict_horizon,
    )
    task_distances = {name: math.dist(starts[name], goals[name]) for name in AGENT_NAMES}
    path_lengths = {name: _path_lengths(paths[name])[1] for name in AGENT_NAMES}
    agents = {}
    for name in AGENT_NAMES:
        goal_heading = math.atan2(
            goals[name][1] - starts[name][1], goals[name][0] - starts[name][0]
        )
        heading = goal_heading + rng.uniform(-0.2, 0.2)
        agents[name] = {
            "start": [round(value, 6) for value in starts[name]],
            "goal": [round(value, 6) for value in goals[name]],
            "heading": round(float(heading), 6),
            "task_distance_m": round(task_distances[name], 6),
            "path_length_m": round(path_lengths[name], 6),
        }

    core = {
        "manifest_version": 1,
        "generator": "fixed-random-v1",
        "preset": config.preset,
        "generation_seed": int(generation_seed),
        "map_id": "TD3.world-v1",
        "num_agents": len(AGENT_NAMES),
        "start_half_width_m": round(half_width, 6),
        "boxes": [[round(value, 6) for value in box] for box in boxes],
        "agents": agents,
        "validity": {
            "static_geometry": True,
            "static_path_for_all_agents": True,
            "gazebo_reset": None,
            "min_start_clearance_m": round(
                pairwise_min_distance(starts.values()), 6
            ),
            "min_goal_clearance_m": round(pairwise_min_distance(goals.values()), 6),
            "min_task_distance_m": round(min(task_distances.values()), 6),
            "max_task_distance_m": round(max(task_distances.values()), 6),
        },
        "metrics": conflict,
    }
    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    core["scenario_id"] = f"{config.preset}-{generation_seed}-{digest}"
    return core


def generate_dataset(config, split_sizes, master_seed, max_candidates=None):
    unknown = set(split_sizes) - set(SPLIT_NAMES)
    if unknown:
        raise ValueError(f"Unsupported splits: {sorted(unknown)}")
    total = sum(int(split_sizes.get(name, 0)) for name in SPLIT_NAMES)
    if total <= 0:
        raise ValueError("At least one scenario must be requested")
    max_candidates = max_candidates or max(total * 20, total + 100)
    accepted = []
    rejected = {}
    candidate_index = 0
    while len(accepted) < total and candidate_index < max_candidates:
        generation_seed = int(master_seed) * 1_000_000 + candidate_index
        candidate_index += 1
        try:
            accepted.append(generate_scenario(generation_seed, config))
        except RuntimeError as exc:
            reason = str(exc)
            rejected[reason] = rejected.get(reason, 0) + 1
    if len(accepted) < total:
        raise RuntimeError(
            f"Generated {len(accepted)}/{total} valid scenarios from {candidate_index} candidates"
        )

    result = {}
    offset = 0
    for split in SPLIT_NAMES:
        size = int(split_sizes.get(split, 0))
        scenarios = accepted[offset : offset + size]
        offset += size
        for scenario in scenarios:
            scenario["split"] = split
        result[split] = {
            "dataset_version": 1,
            "dataset_id": f"{config.preset}-fixed-random-v1-{split}",
            "split": split,
            "generator_config": asdict(config),
            "master_seed": int(master_seed),
            "candidate_count": candidate_index,
            "rejection_counts": rejected,
            "scenarios": scenarios,
        }
    return result


def write_dataset_splits(datasets, output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    written = []
    for split in SPLIT_NAMES:
        payload = datasets.get(split)
        if not payload or not payload["scenarios"]:
            continue
        path = output_path / f"{split}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        written.append(path)
    return written


def load_manifest_dataset(path):
    manifest_path = Path(path)
    opener = gzip.open if manifest_path.suffix == ".gz" else manifest_path.open
    if manifest_path.suffix == ".gz":
        handle_context = opener(manifest_path, "rt", encoding="utf-8")
    else:
        handle_context = opener("r", encoding="utf-8")
    with handle_context as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("scenarios"), list):
        raise ValueError("Manifest dataset must contain a scenarios list")
    if not payload["scenarios"]:
        raise ValueError("Manifest dataset must contain at least one scenario")
    return payload


def validate_manifest_scenarios(scenarios, agent_names):
    """Validate the fixed replay contract without importing ROS."""
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

        agents = scenario.get("agents")
        if not isinstance(agents, dict) or set(agents) != expected_agents:
            raise ValueError(
                f"Manifest scenario {scenario_id} agents must exactly match "
                f"{sorted(expected_agents)}"
            )
        for name in agent_names:
            for key in ("start", "goal"):
                value = agents[name].get(key)
                if not isinstance(value, list) or len(value) != 2:
                    raise ValueError(
                        f"Manifest scenario {scenario_id} {name}.{key} must be [x, y]"
                    )
                if not all(math.isfinite(float(item)) for item in value):
                    raise ValueError(
                        f"Manifest scenario {scenario_id} {name}.{key} must be finite"
                    )
            heading = agents[name].get("heading")
            if heading is None or not math.isfinite(float(heading)):
                raise ValueError(
                    f"Manifest scenario {scenario_id} {name}.heading must be finite"
                )
        boxes = scenario.get("boxes")
        if not isinstance(boxes, list) or len(boxes) > 4:
            raise ValueError(
                f"Manifest scenario {scenario_id} boxes must contain at most 4 positions"
            )
        for box in boxes:
            if not isinstance(box, list) or len(box) != 2:
                raise ValueError(
                    f"Manifest scenario {scenario_id} box positions must be [x, y]"
                )
            if not all(math.isfinite(float(item)) for item in box):
                raise ValueError(
                    f"Manifest scenario {scenario_id} box positions must be finite"
                )
        scenario.setdefault("name", scenario_id)
        scenario["layout"] = "fixed"
        normalized.append(scenario)
    return normalized
