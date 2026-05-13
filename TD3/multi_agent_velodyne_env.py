import math
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


class MultiAgentGazeboEnv:
    """Gazebo environment with multiple robots sharing the same policy."""

    def __init__(
        self,
        launchfile,
        environment_dim,
        agent_names=None,
        cooperative_reward=False,
        reward_neighbor_radius=10.0,
        reward_neighbor_fov=np.pi / 2 + 0.03,
    ):
        self.environment_dim = environment_dim
        self.agent_names = agent_names or ["r1", "r2", "r3"]
        self.num_agents = len(self.agent_names)
        self.cooperative_reward = cooperative_reward
        self.reward_neighbor_radius = reward_neighbor_radius
        self.reward_neighbor_fov = reward_neighbor_fov

        self.upper = 5.0
        self.lower = -5.0

        self.velodyne_data = {
            name: np.ones(self.environment_dim) * 10 for name in self.agent_names
        }
        self.last_odom = {name: None for name in self.agent_names}
        self.goal_positions = {name: np.array([1.0, 0.0]) for name in self.agent_names}
        self.robot_positions = {name: np.array([0.0, 0.0]) for name in self.agent_names}
        self.set_self_states = {name: self._create_model_state(name) for name in self.agent_names}

        self.gaps = [[-np.pi / 2 - 0.03, -np.pi / 2 + np.pi / self.environment_dim]]
        for m in range(self.environment_dim - 1):
            self.gaps.append(
                [self.gaps[m][1], self.gaps[m][1] + np.pi / self.environment_dim]
            )
        self.gaps[-1][-1] += 0.03

        port = "11311"
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

    def set_cooperative_reward(self, enabled):
        self.cooperative_reward = enabled

    def wait_for_odom(self, name, timeout=60.0):
        if self.last_odom[name] is not None:
            return
        try:
            self.last_odom[name] = rospy.wait_for_message(
                f"/{name}/odom", Odometry, timeout=timeout
            )
        except rospy.ROSException as exc:
            raise TimeoutError(
                f"Timed out waiting for /{name}/odom after {timeout} seconds"
            ) from exc

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
        beta = math.acos(dot / (mag1 * mag2))
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

    def _compute_visible_neighbors(self, name):
        neighbors = []
        origin = self.robot_positions[name]
        yaw = self._get_robot_yaw(name)
        heading = np.array([math.cos(yaw), math.sin(yaw)])

        for other_name in self.agent_names:
            if other_name == name:
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
        return neighbors

    def _apply_cooperative_reward(self, rewards, active_mask):
        adjusted = rewards.copy()
        for idx, name in enumerate(self.agent_names):
            if not active_mask[idx]:
                continue
            visible = [name] + self._compute_visible_neighbors(name)
            adjusted[idx] = float(np.mean([rewards[self.agent_names.index(n)] for n in visible]))
        return adjusted

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

        time.sleep(TIME_DELTA)

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

        for idx, name in enumerate(self.agent_names):
            state, distance = self._build_state(name, actions[idx])
            done, collision, min_laser = self.observe_collision(self.velodyne_data[name])
            target = distance < GOAL_REACHED_DIST
            if target:
                done = True
            reward = self.get_reward(target, collision, actions[idx], min_laser)

            if not active_mask[idx]:
                reward = 0.0
                done = True
                collision = False
                target = False

            next_states.append(state)
            rewards.append(reward)
            dones.append(done)
            targets.append(target)
            collisions.append(collision)

        if self.cooperative_reward:
            rewards = self._apply_cooperative_reward(rewards, active_mask)

        return next_states, rewards, dones, targets, collisions

    def reset(self):
        rospy.wait_for_service("/gazebo/reset_world")
        try:
            self.reset_proxy()
        except rospy.ServiceException:
            print("/gazebo/reset_simulation service call failed")

        self.last_odom = {name: None for name in self.agent_names}

        spawn_positions = self._sample_robot_positions()
        for name, position in spawn_positions.items():
            angle = np.random.uniform(-np.pi, np.pi)
            quaternion = Quaternion.from_euler(0.0, 0.0, angle)
            state = self.set_self_states[name]
            state.pose.position.x = position[0]
            state.pose.position.y = position[1]
            state.pose.orientation.x = quaternion.x
            state.pose.orientation.y = quaternion.y
            state.pose.orientation.z = quaternion.z
            state.pose.orientation.w = quaternion.w
            self.set_state.publish(state)
            self.robot_positions[name] = np.array(position)

        self.goal_positions = self._sample_goal_positions()
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

        return [self._build_state(name, [0.0, 0.0])[0] for name in self.agent_names]

    def _sample_robot_positions(self, min_clearance=1.2):
        positions = {}
        for name in self.agent_names:
            placed = False
            while not placed:
                candidate = np.array(
                    [np.random.uniform(-4.5, 4.5), np.random.uniform(-4.5, 4.5)]
                )
                if not check_pos(candidate[0], candidate[1]):
                    continue
                if any(
                    np.linalg.norm(candidate - existing) < min_clearance
                    for existing in positions.values()
                ):
                    continue
                positions[name] = candidate
                placed = True
        return positions

    def _sample_goal_positions(self, min_clearance=1.2):
        goals = {}
        for name in self.agent_names:
            placed = False
            while not placed:
                candidate = np.array(
                    [np.random.uniform(-4.5, 4.5), np.random.uniform(-4.5, 4.5)]
                )
                if not check_pos(candidate[0], candidate[1]):
                    continue
                if np.linalg.norm(candidate - self.robot_positions[name]) < min_clearance:
                    continue
                if any(
                    np.linalg.norm(candidate - other_robot) < min_clearance
                    for other_robot in self.robot_positions.values()
                ):
                    continue
                if any(
                    np.linalg.norm(candidate - existing_goal) < min_clearance
                    for existing_goal in goals.values()
                ):
                    continue
                goals[name] = candidate
                placed = True
        return goals

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

                too_close_robot = any(
                    np.linalg.norm(candidate - robot_pos) < 1.5
                    for robot_pos in self.robot_positions.values()
                )
                too_close_goal = any(
                    np.linalg.norm(candidate - goal_pos) < 1.5
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
            marker.color.r = 0.0
            marker.color.g = 1.0
            marker.color.b = 0.0
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
    def get_reward(target, collision, action, min_laser):
        if target:
            return 100.0
        if collision:
            return -100.0
        r3 = lambda x: 1 - x if x < 1 else 0.0
        return action[0] / 2 - abs(action[1]) / 2 - r3(min_laser) / 2
