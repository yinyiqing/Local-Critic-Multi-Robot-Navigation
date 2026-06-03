import math
import json
import os
import random
import subprocess
import time
from os import path

import numpy as np
import rospy
import sensor_msgs.point_cloud2 as pc2
from gazebo_msgs.msg import ModelState
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from squaternion import Quaternion
from std_srvs.srv import Empty
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray

from velodyne_env import COLLISION_DIST, GOAL_REACHED_DIST, TIME_DELTA, check_pos


AGENT_COLORS = [
    (1.0, 0.20, 0.12),
    (0.15, 0.55, 1.0),
    (0.10, 0.95, 0.35),
    (1.0, 0.75, 0.10),
    (0.85, 0.35, 1.0),
    (0.10, 0.95, 0.95),
    (1.0, 0.45, 0.55),
    (0.55, 0.85, 0.10),
    (0.70, 0.70, 1.0),
    (1.0, 0.55, 0.10),
]


def _env_float(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_range(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise ValueError(f"{name} must be formatted as min,max")
    low, high = float(parts[0]), float(parts[1])
    if low >= high:
        raise ValueError(f"{name} must satisfy min < max")
    return (low, high)


class MultiAgentGazeboEnv:
    """Gazebo environment with multiple robots sharing the same policy."""

    def __init__(
        self,
        launchfile,
        environment_dim,
        agent_names=None,
        cooperative_reward=False,
        cooperative_reward_self_weight=None,
        cooperative_reward_distance_weighted=False,
        cooperative_reward_sigma=2.0,
        cooperative_reward_mode="average",
        interaction_safe_distance=1.2,
        interaction_close_penalty=0.5,
        interaction_stagnation_penalty=0.05,
        anti_stagnation_reward=False,
        anti_stagnation_penalty=0.2,
        anti_stagnation_linear_threshold=0.05,
        anti_stagnation_progress_threshold=0.005,
        anti_stagnation_min_laser=0.35,
        wall_clearance_reward=False,
        wall_clearance_safe_distance=0.75,
        wall_clearance_penalty=1.5,
        wall_clearance_speed_weight=0.8,
        wall_clearance_turn_weight=0.4,
        reward_neighbor_radius=10.0,
        reward_neighbor_fov=np.pi / 2 + 0.03,
        robot_safe_distance=1.0,
        weak_coupling_layout=False,
        scenario_mode="standard",
        active_neighbors_only=False,
    ):
        self.environment_dim = environment_dim
        self.agent_names = agent_names or ["r1", "r2", "r3"]
        self.num_agents = len(self.agent_names)
        self.cooperative_reward = cooperative_reward
        self.cooperative_reward_self_weight = cooperative_reward_self_weight
        self.cooperative_reward_distance_weighted = cooperative_reward_distance_weighted
        self.cooperative_reward_sigma = cooperative_reward_sigma
        self.cooperative_reward_mode = cooperative_reward_mode.strip().lower()
        if self.cooperative_reward_mode not in ("average", "interaction_only"):
            raise ValueError(
                "cooperative_reward_mode must be either 'average' or 'interaction_only'"
            )
        self.interaction_safe_distance = interaction_safe_distance
        self.interaction_close_penalty = interaction_close_penalty
        self.interaction_stagnation_penalty = interaction_stagnation_penalty
        self.anti_stagnation_reward = anti_stagnation_reward
        self.anti_stagnation_penalty = anti_stagnation_penalty
        self.anti_stagnation_linear_threshold = anti_stagnation_linear_threshold
        self.anti_stagnation_progress_threshold = anti_stagnation_progress_threshold
        self.anti_stagnation_min_laser = anti_stagnation_min_laser
        self.wall_clearance_reward = wall_clearance_reward
        self.wall_clearance_safe_distance = wall_clearance_safe_distance
        self.wall_clearance_penalty = wall_clearance_penalty
        self.wall_clearance_speed_weight = wall_clearance_speed_weight
        self.wall_clearance_turn_weight = wall_clearance_turn_weight
        self.reward_neighbor_radius = reward_neighbor_radius
        self.reward_neighbor_fov = reward_neighbor_fov
        self.robot_safe_distance = robot_safe_distance
        self.weak_coupling_layout = weak_coupling_layout
        self.active_neighbors_only = active_neighbors_only
        self.scenario_mode = scenario_mode.strip().lower()
        if self.scenario_mode not in ("standard", "dense", "curriculum"):
            raise ValueError(
                "scenario_mode must be one of: standard, dense, curriculum"
            )
        self.curriculum_cases = []
        self.curriculum_case_index = 0
        self.current_curriculum_case = None
        self.relocate_successful_done_agents = _env_bool(
            "DRL_MULTI_RELOCATE_SUCCESSFUL_DONE_AGENTS", False
        )
        self.done_agent_holding_x = _env_float("DRL_MULTI_DONE_AGENT_HOLDING_X", 20.0)
        self.done_agent_holding_y = _env_float("DRL_MULTI_DONE_AGENT_HOLDING_Y", 20.0)
        self.done_agent_holding_spacing = _env_float(
            "DRL_MULTI_DONE_AGENT_HOLDING_SPACING", 2.0
        )
        if self.relocate_successful_done_agents:
            print(
                "Successful done-agent relocation enabled: holding_origin=(%.2f, %.2f), spacing=%.2f"
                % (
                    self.done_agent_holding_x,
                    self.done_agent_holding_y,
                    self.done_agent_holding_spacing,
                )
            )

        self.upper = 5.0
        self.lower = -5.0
        self.goal_min_distance = 0.8
        self.goal_clearance = 1.2
        self.goal_max_distance = 5.0
        self.capacity_robot_clearance = _env_float(
            "DRL_MULTI_CAPACITY_ROBOT_CLEARANCE", 0.95
        )
        self.capacity_goal_clearance = _env_float(
            "DRL_MULTI_CAPACITY_GOAL_CLEARANCE", 0.85
        )
        self.capacity_robot_goal_clearance = _env_float(
            "DRL_MULTI_CAPACITY_ROBOT_GOAL_CLEARANCE", 0.75
        )
        self.capacity_goal_max_distance = _env_float(
            "DRL_MULTI_CAPACITY_GOAL_MAX_DISTANCE", 3.5
        )
        self.capacity_goal_x_offset = _env_range(
            "DRL_MULTI_CAPACITY_GOAL_X_OFFSET", (-2.2, 2.2)
        )
        self.capacity_goal_y_offset = _env_range(
            "DRL_MULTI_CAPACITY_GOAL_Y_OFFSET", (-2.4, 2.4)
        )
        self.dense_start_x_range = _env_range(
            "DRL_MULTI_DENSE_START_X_RANGE", (-2.0, 2.0)
        )
        self.dense_start_y_range = _env_range(
            "DRL_MULTI_DENSE_START_Y_RANGE", (-2.0, 2.0)
        )
        self.dense_goal_x_offset = _env_range(
            "DRL_MULTI_DENSE_GOAL_X_OFFSET", (-1.2, 1.2)
        )
        self.dense_goal_y_offset = _env_range(
            "DRL_MULTI_DENSE_GOAL_Y_OFFSET", (-1.2, 1.2)
        )
        self.dense_robot_clearance = _env_float(
            "DRL_MULTI_DENSE_ROBOT_CLEARANCE", 0.9
        )
        self.dense_goal_clearance = _env_float("DRL_MULTI_DENSE_GOAL_CLEARANCE", 0.8)
        self.dense_goal_min_distance = _env_float(
            "DRL_MULTI_DENSE_GOAL_MIN_DISTANCE", 0.6
        )
        self.dense_goal_max_distance = _env_float(
            "DRL_MULTI_DENSE_GOAL_MAX_DISTANCE", 2.5
        )
        if self.scenario_mode == "curriculum":
            self.curriculum_cases = self._load_curriculum_cases()
            print(
                "Curriculum scenario enabled: %i cases loaded"
                % len(self.curriculum_cases)
            )

        self.velodyne_data = {
            name: np.ones(self.environment_dim) * 10 for name in self.agent_names
        }
        self.last_odom = {name: None for name in self.agent_names}
        self.previous_distances = {name: None for name in self.agent_names}
        self.goal_positions = {name: np.array([1.0, 0.0]) for name in self.agent_names}
        self.robot_positions = {name: np.array([0.0, 0.0]) for name in self.agent_names}
        self.set_self_states = {name: self._create_model_state(name) for name in self.agent_names}
        self.last_step_info = self._empty_last_step_info()
        self.last_reward_neighbors = {name: [] for name in self.agent_names}
        self.last_interaction_rewards = {name: 0.0 for name in self.agent_names}
        self.last_active_visible_neighbor_counts = {
            name: 0 for name in self.agent_names
        }
        self.success_relocated_agents = set()

        self.gaps = [[-np.pi / 2 - 0.03, -np.pi / 2 + np.pi / self.environment_dim]]
        for m in range(self.environment_dim - 1):
            self.gaps.append(
                [self.gaps[m][1], self.gaps[m][1] + np.pi / self.environment_dim]
            )
        self.gaps[-1][-1] += 0.03

        port = os.environ.get("ROS_PORT_SIM", "11311")
        subprocess.Popen(["roscore", "-p", port])
        print("Roscore launched!")

        rospy.init_node("multi_agent_gym", anonymous=True)
        if launchfile.startswith("/"):
            fullpath = launchfile
        else:
            fullpath = os.path.join(os.path.dirname(__file__), "assets", launchfile)
        if not path.exists(fullpath):
            raise IOError("File " + fullpath + " does not exist")

        subprocess.Popen(["roslaunch", "-p", port, fullpath])
        print("Gazebo launched!")

        self.vel_pubs = {
            name: rospy.Publisher(f"/{name}/cmd_vel", Twist, queue_size=1)
            for name in self.agent_names
        }
        self.set_state = rospy.Publisher("gazebo/set_model_state", ModelState, queue_size=20)
        self.unpause = rospy.ServiceProxy("/gazebo/unpause_physics", Empty)
        self.pause = rospy.ServiceProxy("/gazebo/pause_physics", Empty)
        self.reset_proxy = rospy.ServiceProxy("/gazebo/reset_world", Empty)
        self.goal_publisher = rospy.Publisher("goal_points", MarkerArray, queue_size=10)

        self.velodyne_subscribers = []
        self.odom_subscribers = []
        for name in self.agent_names:
            self.velodyne_subscribers.append(
                rospy.Subscriber(
                    f"/{name}/velodyne_points",
                    PointCloud2,
                    self._make_velodyne_callback(name),
                    queue_size=1,
                )
            )
            self.odom_subscribers.append(
                rospy.Subscriber(
                    f"/{name}/odom",
                    Odometry,
                    self._make_odom_callback(name),
                    queue_size=1,
                )
            )

    @staticmethod
    def _create_model_state(model_name):
        state = ModelState()
        state.model_name = model_name
        state.pose.position.x = 0.0
        state.pose.position.y = 0.0
        state.pose.position.z = 0.0
        state.pose.orientation.x = 0.0
        state.pose.orientation.y = 0.0
        state.pose.orientation.z = 0.0
        state.pose.orientation.w = 1.0
        return state

    def _load_curriculum_cases(self):
        cases_path = os.environ.get("DRL_MULTI_CURRICULUM_CASES", "").strip()
        if not cases_path:
            raise ValueError(
                "DRL_MULTI_CURRICULUM_CASES must point to a JSON case file when "
                "DRL_MULTI_SCENARIO=curriculum"
            )
        if not os.path.isabs(cases_path):
            cases_path = os.path.join(os.getcwd(), cases_path)
        with open(cases_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        cases = payload.get("cases", payload) if isinstance(payload, dict) else payload
        if not isinstance(cases, list) or not cases:
            raise ValueError("Curriculum case file must contain a non-empty case list")
        normalized = []
        for idx, case in enumerate(cases):
            if "agents" not in case or not isinstance(case["agents"], dict):
                raise ValueError(f"Curriculum case {idx} must define an agents object")
            missing = [name for name in self.agent_names if name not in case["agents"]]
            if missing:
                raise ValueError(
                    f"Curriculum case {idx} is missing agents: {', '.join(missing)}"
                )
            normalized.append(case)
        return normalized

    def _select_curriculum_case(self):
        mode = os.environ.get("DRL_MULTI_CURRICULUM_SAMPLING", "cycle").strip().lower()
        if mode == "random":
            weights = [
                max(float(case.get("weight", 1.0)), 0.0)
                for case in self.curriculum_cases
            ]
            if sum(weights) <= 0:
                return random.choice(self.curriculum_cases)
            return random.choices(self.curriculum_cases, weights=weights, k=1)[0]
        if mode != "cycle":
            raise ValueError("DRL_MULTI_CURRICULUM_SAMPLING must be cycle or random")
        case = self.curriculum_cases[self.curriculum_case_index % len(self.curriculum_cases)]
        self.curriculum_case_index += 1
        return case

    def _curriculum_agent_position(self, name, key):
        value = self.current_curriculum_case["agents"][name][key]
        if len(value) != 2:
            raise ValueError(f"{name}.{key} must contain [x, y]")
        return np.array([float(value[0]), float(value[1])])

    def _apply_curriculum_boxes(self):
        boxes = self.current_curriculum_case.get("boxes")
        if boxes is None:
            self.random_box()
            return
        for idx in range(4):
            box_state = ModelState()
            box_state.model_name = "cardboard_box_" + str(idx)
            if idx < len(boxes):
                box = boxes[idx]
                if len(box) != 2:
                    raise ValueError("Each curriculum box must contain [x, y]")
                box_state.pose.position.x = float(box[0])
                box_state.pose.position.y = float(box[1])
            else:
                box_state.pose.position.x = 20.0 + idx
                box_state.pose.position.y = 20.0
            box_state.pose.position.z = 0.0
            box_state.pose.orientation.x = 0.0
            box_state.pose.orientation.y = 0.0
            box_state.pose.orientation.z = 0.0
            box_state.pose.orientation.w = 1.0
            self.set_state.publish(box_state)

    def _holding_position(self, idx):
        return np.array(
            [
                self.done_agent_holding_x + idx * self.done_agent_holding_spacing,
                self.done_agent_holding_y,
            ],
            dtype=np.float32,
        )

    def _relocate_successful_agent(self, name, idx):
        if name in self.success_relocated_agents:
            return
        holding_position = self._holding_position(idx)
        state = self.set_self_states[name]
        state.pose.position.x = float(holding_position[0])
        state.pose.position.y = float(holding_position[1])
        state.pose.position.z = 0.0
        state.pose.orientation.x = 0.0
        state.pose.orientation.y = 0.0
        state.pose.orientation.z = 0.0
        state.pose.orientation.w = 1.0
        state.twist.linear.x = 0.0
        state.twist.linear.y = 0.0
        state.twist.linear.z = 0.0
        state.twist.angular.x = 0.0
        state.twist.angular.y = 0.0
        state.twist.angular.z = 0.0
        self.set_state.publish(state)
        self.robot_positions[name] = holding_position
        self.last_odom[name] = None
        self.success_relocated_agents.add(name)

    def _make_velodyne_callback(self, name):
        def callback(msg):
            data = list(pc2.read_points(msg, skip_nans=False, field_names=("x", "y", "z")))
            agent_scan = np.ones(self.environment_dim) * 10
            for point in data:
                if point[2] <= -0.2:
                    continue
                dot = point[0]
                mag1 = math.sqrt(point[0] ** 2 + point[1] ** 2)
                if mag1 == 0:
                    continue
                beta = math.acos(dot / mag1) * np.sign(point[1])
                dist = math.sqrt(point[0] ** 2 + point[1] ** 2 + point[2] ** 2)

                for idx, gap in enumerate(self.gaps):
                    if gap[0] <= beta < gap[1]:
                        agent_scan[idx] = min(agent_scan[idx], dist)
                        break
            self.velodyne_data[name] = agent_scan

        return callback

    def _make_odom_callback(self, name):
        def callback(msg):
            self.last_odom[name] = msg

        return callback

    def _empty_last_step_info(self):
        return {
            "agents": {
                name: {
                    "target": False,
                    "collision": False,
                    "distance": None,
                    "progress": 0.0,
                    "min_laser": None,
                    "nearest_robot_distance": None,
                    "reward": 0.0,
                    "raw_reward": 0.0,
                    "interaction_reward": 0.0,
                    "anti_stagnation_reward": 0.0,
                    "wall_clearance_reward": 0.0,
                    "reward_neighbors": [],
                    "active_visible_neighbor_count": 0,
                    "nearest_active_visible_neighbor_distance": None,
                    "relocated_to_holding": False,
                }
                for name in self.agent_names
            },
            "mean_reward": 0.0,
            "success_count": 0,
            "collision_count": 0,
            "relocated_successful_count": 0,
            "relocated_successful_agents": [],
            "active_neighbor_agent_count": 0,
            "mean_active_visible_neighbors": 0.0,
            "max_active_visible_neighbors": 0,
            "mean_interaction_reward": 0.0,
            "mean_anti_stagnation_reward": 0.0,
        }

    def set_cooperative_reward(self, enabled):
        self.cooperative_reward = enabled

    def set_anti_stagnation_reward(self, enabled):
        self.anti_stagnation_reward = enabled

    def set_wall_clearance_reward(self, enabled):
        self.wall_clearance_reward = enabled

    def wait_for_odom(self, name, timeout=60.0, recover_with_unpause=True):
        if self.last_odom[name] is not None:
            return
        if recover_with_unpause:
            try:
                rospy.wait_for_service("/gazebo/unpause_physics", timeout=5.0)
                self.unpause()
                time.sleep(max(TIME_DELTA, 0.2))
            except (rospy.ROSException, rospy.ServiceException):
                pass
        try:
            self.last_odom[name] = rospy.wait_for_message(
                f"/{name}/odom", Odometry, timeout=timeout
            )
            return
        except rospy.ROSException as exc:
            if not recover_with_unpause:
                raise TimeoutError(
                    f"Timed out waiting for /{name}/odom after {timeout} seconds"
                ) from exc
            try:
                rospy.wait_for_service("/gazebo/unpause_physics", timeout=5.0)
                self.unpause()
                time.sleep(max(TIME_DELTA * 2, 0.4))
                self.last_odom[name] = rospy.wait_for_message(
                    f"/{name}/odom", Odometry, timeout=timeout
                )
                return
            except (rospy.ROSException, rospy.ServiceException) as retry_exc:
                raise TimeoutError(
                    f"Timed out waiting for /{name}/odom after reset recovery"
                ) from retry_exc

    def wait_for_all_odom(self, timeout_per_agent=2.0, attempts=5):
        missing = []
        for attempt in range(attempts):
            missing = []
            for name in self.agent_names:
                if self.last_odom[name] is not None:
                    continue
                try:
                    self.wait_for_odom(
                        name,
                        timeout=timeout_per_agent,
                        recover_with_unpause=False,
                    )
                except TimeoutError:
                    missing.append(name)
            if not missing:
                return
            try:
                rospy.wait_for_service("/gazebo/unpause_physics", timeout=5.0)
                self.unpause()
            except (rospy.ROSException, rospy.ServiceException):
                pass
            time.sleep(TIME_DELTA)
        raise TimeoutError(
            "Timed out waiting for odom topics after reset: "
            + ", ".join(f"/{name}/odom" for name in missing)
        )

    def _get_robot_yaw(self, name):
        odom = self.last_odom[name]
        quaternion = Quaternion(
            odom.pose.pose.orientation.w,
            odom.pose.pose.orientation.x,
            odom.pose.pose.orientation.y,
            odom.pose.pose.orientation.z,
        )
        euler = quaternion.to_euler(degrees=False)
        return round(euler[2], 4)

    def _build_state(self, name, action):
        self.wait_for_odom(name)
        odom = self.last_odom[name]
        self.robot_positions[name] = np.array(
            [odom.pose.pose.position.x, odom.pose.pose.position.y]
        )
        angle = self._get_robot_yaw(name)

        goal_x, goal_y = self.goal_positions[name]
        distance = np.linalg.norm(self.robot_positions[name] - self.goal_positions[name])

        skew_x = goal_x - self.robot_positions[name][0]
        skew_y = goal_y - self.robot_positions[name][1]
        dot = skew_x
        mag1 = math.sqrt(skew_x ** 2 + skew_y ** 2)
        mag2 = 1.0
        cos_beta = np.clip(dot / (mag1 * mag2), -1.0, 1.0) if mag1 > 0 else 1.0
        beta = math.acos(cos_beta)
        if skew_y < 0:
            if skew_x < 0:
                beta = -beta
            else:
                beta = -beta
        theta = beta - angle

        if theta > np.pi:
            theta = np.pi - theta
            theta = -np.pi - theta
        if theta < -np.pi:
            theta = -np.pi - theta
            theta = np.pi - theta

        robot_state = [distance, theta, action[0], action[1]]
        return np.append([self.velodyne_data[name]], robot_state), distance

    def _compute_visible_neighbors(self, name, active_names=None):
        neighbors = []
        origin = self.robot_positions[name]
        yaw = self._get_robot_yaw(name)
        heading = np.array([math.cos(yaw), math.sin(yaw)])

        for other_name in self.agent_names:
            if other_name == name:
                continue
            if active_names is not None and other_name not in active_names:
                continue
            offset = self.robot_positions[other_name] - origin
            distance = np.linalg.norm(offset)
            if distance == 0 or distance > self.reward_neighbor_radius:
                continue

            direction = offset / distance
            dot = np.clip(np.dot(heading, direction), -1.0, 1.0)
            relative_angle = math.acos(dot)
            if relative_angle <= self.reward_neighbor_fov:
                neighbors.append(other_name)
        neighbors.sort(
            key=lambda other: np.linalg.norm(self.robot_positions[other] - origin)
        )
        return neighbors

    def build_neighbor_context(
        self, actions, max_neighbors=9, include_actions=True, active_mask=None
    ):
        contexts = []
        feature_dim = 7 if include_actions else 5
        active_names = None
        if self.active_neighbors_only and active_mask is not None:
            active_names = {
                name
                for idx, name in enumerate(self.agent_names)
                if idx < len(active_mask) and active_mask[idx]
            }
        action_by_name = {
            name: np.array(actions[idx], dtype=np.float32)
            for idx, name in enumerate(self.agent_names)
        }

        for name in self.agent_names:
            if active_names is not None and name not in active_names:
                contexts.append(np.zeros(max_neighbors * feature_dim, dtype=np.float32))
                continue
            origin = self.robot_positions[name]
            yaw = self._get_robot_yaw(name)
            context = []
            for other_name in self._compute_visible_neighbors(
                name, active_names=active_names
            )[:max_neighbors]:
                offset = self.robot_positions[other_name] - origin
                distance = float(np.linalg.norm(offset))
                bearing = math.atan2(offset[1], offset[0]) - yaw
                while bearing > np.pi:
                    bearing -= 2 * np.pi
                while bearing < -np.pi:
                    bearing += 2 * np.pi
                neighbor_features = [
                    float(offset[0]),
                    float(offset[1]),
                    distance,
                    float(bearing),
                ]
                if include_actions:
                    other_action = action_by_name.get(other_name, np.zeros(2))
                    neighbor_features.extend(
                        [float(other_action[0]), float(other_action[1])]
                    )
                neighbor_features.append(1.0)
                context.extend(neighbor_features)

            missing = max_neighbors - len(context) // feature_dim
            if missing > 0:
                context.extend([0.0] * missing * feature_dim)
            contexts.append(np.array(context, dtype=np.float32))
        return contexts

    def _apply_cooperative_reward(self, rewards, active_mask, step_agents_info=None):
        adjusted = rewards.copy()
        self.last_reward_neighbors = {name: [] for name in self.agent_names}
        self.last_interaction_rewards = {name: 0.0 for name in self.agent_names}
        self.last_active_visible_neighbor_counts = {
            name: 0 for name in self.agent_names
        }
        active_names = None
        if self.active_neighbors_only:
            active_names = {
                name
                for idx, name in enumerate(self.agent_names)
                if idx < len(active_mask) and active_mask[idx]
            }
        for idx, name in enumerate(self.agent_names):
            if not active_mask[idx]:
                continue
            visible_neighbors = self._compute_visible_neighbors(
                name, active_names=active_names
            )
            visible = [name] + visible_neighbors
            self.last_reward_neighbors[name] = [n for n in visible if n != name]
            self.last_active_visible_neighbor_counts[name] = len(
                self.last_reward_neighbors[name]
            )
            if self.cooperative_reward_mode == "interaction_only":
                interaction_reward = self._compute_interaction_reward(
                    name,
                    self.last_reward_neighbors[name],
                    step_agents_info[name]["progress"] if step_agents_info else 0.0,
                )
                self.last_interaction_rewards[name] = interaction_reward
                adjusted[idx] = float(rewards[idx] + interaction_reward)
                continue
            if (
                self.cooperative_reward_self_weight is not None
                and self.last_reward_neighbors[name]
            ):
                self_weight = float(self.cooperative_reward_self_weight)
                neighbor_rewards = np.array(
                    [
                        rewards[self.agent_names.index(n)]
                        for n in self.last_reward_neighbors[name]
                    ],
                    dtype=np.float32,
                )
                if self.cooperative_reward_distance_weighted:
                    distances = np.array(
                        [
                            np.linalg.norm(
                                self.robot_positions[n] - self.robot_positions[name]
                            )
                            for n in self.last_reward_neighbors[name]
                        ],
                        dtype=np.float32,
                    )
                    sigma = max(float(self.cooperative_reward_sigma), 1e-6)
                    weights = np.exp(-distances / sigma)
                    neighbor_reward = float(np.sum(weights * neighbor_rewards) / np.sum(weights))
                else:
                    neighbor_reward = float(np.mean(neighbor_rewards))
                adjusted[idx] = float(
                    self_weight * rewards[idx]
                    + (1.0 - self_weight) * neighbor_reward
                )
            else:
                adjusted[idx] = float(
                    np.mean([rewards[self.agent_names.index(n)] for n in visible])
                )
        return adjusted

    def _compute_interaction_reward(self, name, visible_neighbors, progress):
        if not visible_neighbors:
            return 0.0

        distances = np.array(
            [
                np.linalg.norm(self.robot_positions[other_name] - self.robot_positions[name])
                for other_name in visible_neighbors
            ],
            dtype=np.float32,
        )
        safe_distance = max(float(self.interaction_safe_distance), 1e-6)
        close_pressure = np.maximum(0.0, safe_distance - distances) / safe_distance
        close_penalty = float(np.mean(close_pressure))

        stagnation_penalty = 0.0
        if progress < 0.002:
            stagnation_penalty = float(self.interaction_stagnation_penalty)

        return -float(self.interaction_close_penalty) * close_penalty - stagnation_penalty

    def _compute_anti_stagnation_penalty(
        self, target, collision, action, min_laser, progress
    ):
        if not self.anti_stagnation_reward or target or collision:
            return 0.0
        if min_laser is None or min_laser < self.anti_stagnation_min_laser:
            return 0.0
        if (
            action[0] < self.anti_stagnation_linear_threshold
            and abs(progress) < self.anti_stagnation_progress_threshold
        ):
            return float(self.anti_stagnation_penalty)
        return 0.0

    def _compute_wall_clearance_penalty(self, target, collision, action, min_laser):
        if not self.wall_clearance_reward or target or collision:
            return 0.0
        if min_laser is None:
            return 0.0
        safe_distance = max(float(self.wall_clearance_safe_distance), COLLISION_DIST)
        if min_laser >= safe_distance:
            return 0.0
        pressure = (safe_distance - min_laser) / safe_distance
        motion_scale = (
            1.0
            + self.wall_clearance_speed_weight * max(float(action[0]), 0.0)
            + self.wall_clearance_turn_weight * abs(float(action[1]))
        )
        return float(self.wall_clearance_penalty) * pressure * motion_scale

    def _nearest_robot_distance(self, name):
        origin = self.robot_positions[name]
        distances = []
        for other_name in self.agent_names:
            if other_name == name:
                continue
            distances.append(np.linalg.norm(self.robot_positions[other_name] - origin))
        if not distances:
            return float("inf")
        return float(min(distances))

    def _uses_capacity_layout(self):
        return (
            self.scenario_mode == "standard"
            and self.weak_coupling_layout
            and self.num_agents >= 5
        )

    def _sample_position(self, x_range, y_range):
        for _ in range(500):
            candidate = np.array(
                [np.random.uniform(*x_range), np.random.uniform(*y_range)]
            )
            if check_pos(candidate[0], candidate[1]):
                return candidate
        raise RuntimeError(
            "Could not sample a valid position in range "
            f"x={x_range}, y={y_range}. Check map capacity and obstacles."
        )

    def _agent_side_ranges(self, name):
        if self.scenario_mode == "dense":
            return self.dense_start_x_range, self.dense_start_y_range
        if not self.weak_coupling_layout:
            return (-4.5, 4.5), (-4.5, 4.5)
        if self.num_agents > 2:
            return (-4.5, 4.5), (-4.5, 4.5)
        if name == self.agent_names[0]:
            return (-4.2, -1.0), (-4.2, 4.2)
        return (1.0, 4.2), (-4.2, 4.2)

    def _sample_goal_candidate_for_agent(self, name):
        if self.scenario_mode == "dense":
            x_range, y_range = self._agent_side_ranges(name)
            while True:
                x_offset = random.uniform(*self.dense_goal_x_offset)
                y_offset = random.uniform(*self.dense_goal_y_offset)
                candidate = np.array(
                    [
                        np.clip(
                            self.robot_positions[name][0] + x_offset,
                            x_range[0],
                            x_range[1],
                        ),
                        np.clip(
                            self.robot_positions[name][1] + y_offset,
                            y_range[0],
                            y_range[1],
                        ),
                    ]
                )
                if (
                    np.linalg.norm(candidate - self.robot_positions[name])
                    < self.dense_goal_min_distance
                ):
                    continue
                return candidate

        if not self.weak_coupling_layout:
            return np.array(
                [
                    self.robot_positions[name][0] + random.uniform(self.lower, self.upper),
                    self.robot_positions[name][1] + random.uniform(self.lower, self.upper),
                ]
            )

        x_range, y_range = self._agent_side_ranges(name)
        if self._uses_capacity_layout():
            x_offset_range = self.capacity_goal_x_offset
            y_offset_range = self.capacity_goal_y_offset
        else:
            x_offset_range = (-1.8, 1.8)
            y_offset_range = (-2.2, 2.2)
        while True:
            x_offset = random.uniform(*x_offset_range)
            y_offset = random.uniform(*y_offset_range)
            candidate = np.array(
                [
                    np.clip(self.robot_positions[name][0] + x_offset, x_range[0], x_range[1]),
                    np.clip(self.robot_positions[name][1] + y_offset, y_range[0], y_range[1]),
                ]
            )
            if np.linalg.norm(candidate - self.robot_positions[name]) < self.goal_min_distance:
                continue
            return candidate

    def _sample_start_heading(self, name):
        if self.scenario_mode == "curriculum":
            agent_case = self.current_curriculum_case["agents"][name]
            if "heading" in agent_case:
                return float(agent_case["heading"])
        goal_offset = self.goal_positions[name] - self.robot_positions[name]
        goal_heading = math.atan2(goal_offset[1], goal_offset[0])
        return goal_heading + np.random.uniform(-0.2, 0.2)

    def step(self, actions, active_mask=None):
        if active_mask is None:
            active_mask = [True] * self.num_agents

        for idx, name in enumerate(self.agent_names):
            command = Twist()
            if active_mask[idx]:
                command.linear.x = actions[idx][0]
                command.angular.z = actions[idx][1]
            self.vel_pubs[name].publish(command)

        self.publish_goal_markers()

        rospy.wait_for_service("/gazebo/unpause_physics")
        try:
            self.unpause()
        except rospy.ServiceException:
            print("/gazebo/unpause_physics service call failed")

        time.sleep(max(TIME_DELTA, 0.2))
        self.wait_for_all_odom()

        rospy.wait_for_service("/gazebo/pause_physics")
        try:
            self.pause()
        except rospy.ServiceException:
            print("/gazebo/pause_physics service call failed")

        next_states = []
        rewards = []
        dones = []
        targets = []
        collisions = []
        step_agents_info = {}

        for idx, name in enumerate(self.agent_names):
            state, distance = self._build_state(name, actions[idx])
            done, collision, min_laser = self.observe_collision(self.velodyne_data[name])
            target = distance < GOAL_REACHED_DIST
            if target:
                done = True
            progress = (
                0.0
                if self.previous_distances[name] is None
                else self.previous_distances[name] - distance
            )
            reward = self.get_reward(target, collision, actions[idx], min_laser, progress)
            anti_stagnation_penalty = self._compute_anti_stagnation_penalty(
                target, collision, actions[idx], min_laser, progress
            )
            reward -= anti_stagnation_penalty
            wall_clearance_penalty = self._compute_wall_clearance_penalty(
                target, collision, actions[idx], min_laser
            )
            reward -= wall_clearance_penalty
            self.previous_distances[name] = distance
            nearest_robot_distance = self._nearest_robot_distance(name)
            if (
                self.robot_safe_distance > 0.0
                and np.isfinite(nearest_robot_distance)
                and nearest_robot_distance < self.robot_safe_distance
            ):
                reward -= 5.0 * (self.robot_safe_distance - nearest_robot_distance)

            if not active_mask[idx]:
                reward = 0.0
                done = True
                collision = False
                target = False
                progress = 0.0
                anti_stagnation_penalty = 0.0
                wall_clearance_penalty = 0.0
                nearest_robot_distance = None

            next_states.append(state)
            rewards.append(reward)
            dones.append(done)
            targets.append(target)
            collisions.append(collision)
            step_agents_info[name] = {
                "target": target,
                "collision": collision,
                "distance": distance,
                "progress": progress,
                "min_laser": min_laser,
                "nearest_robot_distance": nearest_robot_distance,
                "reward": reward,
                "raw_reward": reward,
                "interaction_reward": 0.0,
                "anti_stagnation_reward": -anti_stagnation_penalty,
                "wall_clearance_reward": -wall_clearance_penalty,
                "reward_neighbors": [],
                "active_visible_neighbor_count": 0,
                "nearest_active_visible_neighbor_distance": None,
                "relocated_to_holding": False,
            }

        if self.cooperative_reward:
            rewards = self._apply_cooperative_reward(
                rewards, active_mask, step_agents_info
            )
            for idx, name in enumerate(self.agent_names):
                step_agents_info[name]["reward"] = rewards[idx]
                step_agents_info[name]["reward_neighbors"] = self.last_reward_neighbors[
                    name
                ]
                step_agents_info[name]["interaction_reward"] = (
                    self.last_interaction_rewards[name]
                )
                step_agents_info[name]["active_visible_neighbor_count"] = (
                    self.last_active_visible_neighbor_counts[name]
                )
                active_neighbor_distances = [
                    float(
                        np.linalg.norm(
                            self.robot_positions[other_name]
                            - self.robot_positions[name]
                        )
                    )
                    for other_name in self.last_reward_neighbors[name]
                ]
                if active_neighbor_distances:
                    step_agents_info[name][
                        "nearest_active_visible_neighbor_distance"
                    ] = min(active_neighbor_distances)

        active_neighbor_counts = [
            step_agents_info[name]["active_visible_neighbor_count"]
            for idx, name in enumerate(self.agent_names)
            if idx < len(active_mask) and active_mask[idx]
        ]
        interaction_rewards = [
            step_agents_info[name]["interaction_reward"]
            for idx, name in enumerate(self.agent_names)
            if idx < len(active_mask) and active_mask[idx]
        ]
        anti_stagnation_rewards = [
            step_agents_info[name]["anti_stagnation_reward"]
            for idx, name in enumerate(self.agent_names)
            if idx < len(active_mask) and active_mask[idx]
        ]
        wall_clearance_rewards = [
            step_agents_info[name]["wall_clearance_reward"]
            for idx, name in enumerate(self.agent_names)
            if idx < len(active_mask) and active_mask[idx]
        ]
        relocated_successful_agents = []
        if self.relocate_successful_done_agents:
            for idx, name in enumerate(self.agent_names):
                if idx < len(active_mask) and active_mask[idx] and targets[idx]:
                    self._relocate_successful_agent(name, idx)
                    step_agents_info[name]["relocated_to_holding"] = True
                    relocated_successful_agents.append(name)

        self.last_step_info = {
            "agents": step_agents_info,
            "mean_reward": float(np.mean(rewards)) if rewards else 0.0,
            "success_count": int(sum(int(flag) for flag in targets)),
            "collision_count": int(sum(int(flag) for flag in collisions)),
            "relocated_successful_count": len(relocated_successful_agents),
            "relocated_successful_agents": relocated_successful_agents,
            "active_neighbor_agent_count": int(
                sum(1 for count in active_neighbor_counts if count > 0)
            ),
            "mean_active_visible_neighbors": (
                float(np.mean(active_neighbor_counts)) if active_neighbor_counts else 0.0
            ),
            "max_active_visible_neighbors": (
                int(max(active_neighbor_counts)) if active_neighbor_counts else 0
            ),
            "mean_interaction_reward": (
                float(np.mean(interaction_rewards)) if interaction_rewards else 0.0
            ),
            "mean_anti_stagnation_reward": (
                float(np.mean(anti_stagnation_rewards))
                if anti_stagnation_rewards
                else 0.0
            ),
            "mean_wall_clearance_reward": (
                float(np.mean(wall_clearance_rewards))
                if wall_clearance_rewards
                else 0.0
            ),
        }

        return next_states, rewards, dones, targets, collisions

    def reset(self):
        rospy.wait_for_service("/gazebo/reset_world")
        try:
            self.reset_proxy()
        except rospy.ServiceException:
            print("/gazebo/reset_simulation service call failed")

        if self.upper < 10:
            self.upper += 0.004
        if self.lower > -10:
            self.lower -= 0.004

        self.last_odom = {name: None for name in self.agent_names}
        self.previous_distances = {name: None for name in self.agent_names}
        self.success_relocated_agents = set()
        self.last_step_info = self._empty_last_step_info()

        last_error = None
        for reset_attempt in range(20):
            try:
                if self.scenario_mode == "curriculum":
                    self.current_curriculum_case = self._select_curriculum_case()
                spawn_positions = self._sample_robot_positions()
                for name, position in spawn_positions.items():
                    self.robot_positions[name] = np.array(position)
                self.goal_positions = self._sample_goal_positions()
                break
            except RuntimeError as exc:
                last_error = exc
                print(
                    "Reset placement retry %i/20 failed: %s"
                    % (reset_attempt + 1, exc)
                )
        else:
            raise RuntimeError(
                "Could not sample a valid multi-agent reset after 20 attempts. "
                f"Last error: {last_error}"
            )

        for name, position in spawn_positions.items():
            angle = self._sample_start_heading(name)
            quaternion = Quaternion.from_euler(0.0, 0.0, angle)
            state = self.set_self_states[name]
            state.pose.position.x = position[0]
            state.pose.position.y = position[1]
            state.pose.orientation.x = quaternion.x
            state.pose.orientation.y = quaternion.y
            state.pose.orientation.z = quaternion.z
            state.pose.orientation.w = quaternion.w
            self.set_state.publish(state)

        if self.scenario_mode == "curriculum":
            self._apply_curriculum_boxes()
        else:
            self.random_box()
        self.publish_goal_markers()

        rospy.wait_for_service("/gazebo/unpause_physics")
        try:
            self.unpause()
        except rospy.ServiceException:
            print("/gazebo/unpause_physics service call failed")

        time.sleep(TIME_DELTA)

        rospy.wait_for_service("/gazebo/pause_physics")
        try:
            self.pause()
        except rospy.ServiceException:
            print("/gazebo/pause_physics service call failed")

        initial_states = []
        for name in self.agent_names:
            state, distance = self._build_state(name, [0.0, 0.0])
            self.previous_distances[name] = distance
            self.last_step_info["agents"][name]["distance"] = distance
            self.last_step_info["agents"][name]["min_laser"] = float(
                np.min(self.velodyne_data[name])
            )
            initial_states.append(state)
        return initial_states

    def _sample_robot_positions(self, min_clearance=1.2):
        if self.scenario_mode == "curriculum":
            return {
                name: self._curriculum_agent_position(name, "start")
                for name in self.agent_names
            }
        if self.scenario_mode == "dense":
            min_clearance = self.dense_robot_clearance
        elif self._uses_capacity_layout():
            min_clearance = min(min_clearance, self.capacity_robot_clearance)
        if self.weak_coupling_layout:
            if self.num_agents <= 2:
                min_clearance = max(min_clearance, 3.0)
            elif not self._uses_capacity_layout():
                min_clearance = max(min_clearance, 1.2)
        positions = {}
        for name in self.agent_names:
            placed = False
            for _ in range(1000):
                x_range, y_range = self._agent_side_ranges(name)
                candidate = self._sample_position(x_range, y_range)
                if any(
                    np.linalg.norm(candidate - existing) < min_clearance
                    for existing in positions.values()
                ):
                    continue
                positions[name] = candidate
                placed = True
                break
            if not placed:
                raise RuntimeError(
                    f"Could not place robot {name} with clearance {min_clearance}. "
                    f"Placed {len(positions)}/{self.num_agents} robots. "
                    "The map may be too crowded for this robot count."
                )
        return positions

    def _sample_goal_positions(self, min_clearance=1.2):
        if self.scenario_mode == "curriculum":
            return {
                name: self._curriculum_agent_position(name, "goal")
                for name in self.agent_names
            }
        if self.scenario_mode == "dense":
            min_clearance = self.dense_goal_clearance
            goal_min_distance = self.dense_goal_min_distance
            goal_max_distance = self.dense_goal_max_distance
            robot_goal_clearance = self.dense_goal_clearance
        elif self._uses_capacity_layout():
            min_clearance = min(min_clearance, self.capacity_goal_clearance)
            goal_min_distance = self.goal_min_distance
            goal_max_distance = self.capacity_goal_max_distance
            robot_goal_clearance = self.capacity_robot_goal_clearance
        else:
            goal_min_distance = self.goal_min_distance
            goal_max_distance = self.goal_max_distance
            robot_goal_clearance = self.goal_clearance

        clearance_schedule = [min_clearance]
        if self.scenario_mode == "dense":
            clearance_schedule = [
                min_clearance,
                max(min_clearance * 0.75, 0.55),
                max(min_clearance * 0.6, 0.45),
            ]
        elif self.weak_coupling_layout:
            if self.num_agents <= 2:
                clearance_schedule = [max(min_clearance, 1.8), min_clearance]
            elif self._uses_capacity_layout():
                clearance_schedule = [
                    min_clearance,
                    max(min_clearance * 0.8, 0.65),
                    max(min_clearance * 0.65, 0.55),
                    max(min_clearance * 0.5, 0.45),
                ]
            else:
                clearance_schedule = [min_clearance, 1.0, 0.8]

        last_error = None
        for clearance in clearance_schedule:
            goals = {}
            for name in self.agent_names:
                placed = False
                for _ in range(2000):
                    candidate = self._sample_goal_candidate_for_agent(name)
                    if not check_pos(candidate[0], candidate[1]):
                        continue
                    goal_distance = np.linalg.norm(
                        candidate - self.robot_positions[name]
                    )
                    if (
                        goal_distance < goal_min_distance
                        or goal_distance > goal_max_distance
                    ):
                        continue
                    if any(
                        np.linalg.norm(candidate - other_robot) < robot_goal_clearance
                        for other_robot in self.robot_positions.values()
                    ):
                        continue
                    if any(
                        np.linalg.norm(candidate - existing_goal) < clearance
                        for existing_goal in goals.values()
                    ):
                        continue
                    goals[name] = candidate
                    placed = True
                    break
                if not placed:
                    last_error = (
                        f"Could not place goal for {name} with clearance {clearance}. "
                        f"Placed {len(goals)}/{self.num_agents} goals."
                    )
                    break
            if len(goals) == self.num_agents:
                if clearance < min_clearance:
                    print(
                        "Goal placement used relaxed clearance %.2f for %i agents"
                        % (clearance, self.num_agents)
                    )
                return goals

        raise RuntimeError(
            f"{last_error} The map may be too crowded for this robot count."
        )

    def random_box(self):
        for i in range(4):
            name = "cardboard_box_" + str(i)
            box_ok = False
            while not box_ok:
                candidate = np.array(
                    [np.random.uniform(-6, 6), np.random.uniform(-6, 6)]
                )
                if not check_pos(candidate[0], candidate[1]):
                    continue

                if self._uses_capacity_layout():
                    clearance = 1.0
                else:
                    clearance = 2.0 if self.weak_coupling_layout else 1.5
                too_close_robot = any(
                    np.linalg.norm(candidate - robot_pos) < clearance
                    for robot_pos in self.robot_positions.values()
                )
                too_close_goal = any(
                    np.linalg.norm(candidate - goal_pos) < clearance
                    for goal_pos in self.goal_positions.values()
                )
                if too_close_robot or too_close_goal:
                    continue
                box_ok = True

            box_state = ModelState()
            box_state.model_name = name
            box_state.pose.position.x = candidate[0]
            box_state.pose.position.y = candidate[1]
            box_state.pose.position.z = 0.0
            box_state.pose.orientation.x = 0.0
            box_state.pose.orientation.y = 0.0
            box_state.pose.orientation.z = 0.0
            box_state.pose.orientation.w = 1.0
            self.set_state.publish(box_state)

    def publish_goal_markers(self):
        marker_array = MarkerArray()
        for idx, name in enumerate(self.agent_names):
            marker = Marker()
            marker.header.frame_id = "odom"
            marker.ns = "goal_points"
            marker.id = idx
            marker.type = marker.CYLINDER
            marker.action = marker.ADD
            marker.scale.x = 0.15
            marker.scale.y = 0.15
            marker.scale.z = 0.02
            marker.color.a = 1.0
            color = AGENT_COLORS[idx % len(AGENT_COLORS)]
            marker.color.r = color[0]
            marker.color.g = color[1]
            marker.color.b = color[2]
            marker.pose.orientation.w = 1.0
            marker.pose.position.x = self.goal_positions[name][0]
            marker.pose.position.y = self.goal_positions[name][1]
            marker.pose.position.z = 0.0
            marker_array.markers.append(marker)
        self.goal_publisher.publish(marker_array)

    @staticmethod
    def observe_collision(laser_data):
        min_laser = min(laser_data)
        if min_laser < COLLISION_DIST:
            return True, True, min_laser
        return False, False, min_laser

    @staticmethod
    def get_reward(target, collision, action, min_laser, progress):
        if target:
            return 100.0
        if collision:
            return -100.0
        obstacle_penalty = 1 - min_laser if min_laser < 1 else 0.0
        progress_reward = 20.0 * progress
        forward_reward = 0.5 * action[0]
        turn_penalty = 0.2 * abs(action[1])
        stagnation_penalty = 0.03 if action[0] < 0.1 and abs(progress) < 0.01 else 0.0
        return (
            progress_reward
            + forward_reward
            - turn_penalty
            - 0.5 * obstacle_penalty
            - stagnation_penalty
        )
