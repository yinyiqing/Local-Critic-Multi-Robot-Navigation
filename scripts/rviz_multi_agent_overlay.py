#!/usr/bin/env python3
import argparse
import math
from collections import deque

import rospy
from geometry_msgs.msg import Point
from nav_msgs.msg import Odometry
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray


COLORS = [
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


OBSTACLES = [
    (-6.2, -3.8, 3.8, 6.2),
    (-2.7, -1.3, -0.2, 4.7),
    (-4.2, -0.3, 1.3, 2.7),
    (-4.2, -0.8, -4.2, -2.3),
    (-3.7, -1.3, -2.7, -0.8),
    (0.8, 4.2, -3.2, -1.8),
    (2.5, 4.0, -3.2, 0.7),
    (3.8, 6.2, -4.2, -3.3),
    (1.3, 4.2, 1.5, 3.7),
    (-7.2, -3.0, -1.5, 0.5),
]


class MultiAgentOverlay:
    def __init__(self, agent_names, frame_id, trail_length):
        self.agent_names = agent_names
        self.frame_id = frame_id
        self.trails = {name: deque(maxlen=trail_length) for name in agent_names}
        self.poses = {}
        self.publisher = rospy.Publisher(
            "/multi_agent_overlay", MarkerArray, queue_size=1
        )
        self.subscribers = [
            rospy.Subscriber(
                f"/{name}/odom",
                Odometry,
                self._make_odom_callback(name),
                queue_size=1,
            )
            for name in agent_names
        ]

    def _make_odom_callback(self, name):
        def callback(msg):
            pose = msg.pose.pose
            self.poses[name] = pose
            self.trails[name].append((pose.position.x, pose.position.y))

        return callback

    @staticmethod
    def _yaw_from_pose(pose):
        q = pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    @staticmethod
    def _set_color(marker, color, alpha):
        marker.color.r = color[0]
        marker.color.g = color[1]
        marker.color.b = color[2]
        marker.color.a = alpha

    def _delete_all_marker(self):
        marker = Marker()
        marker.action = Marker.DELETEALL
        return marker

    def _obstacle_markers(self):
        markers = []
        for idx, (xmin, xmax, ymin, ymax) in enumerate(OBSTACLES):
            marker = Marker()
            marker.header.frame_id = self.frame_id
            marker.header.stamp = rospy.Time.now()
            marker.ns = "static_obstacles"
            marker.id = idx
            marker.type = Marker.CUBE
            marker.action = Marker.ADD
            marker.pose.position.x = (xmin + xmax) / 2.0
            marker.pose.position.y = (ymin + ymax) / 2.0
            marker.pose.position.z = -0.02
            marker.pose.orientation.w = 1.0
            marker.scale.x = abs(xmax - xmin)
            marker.scale.y = abs(ymax - ymin)
            marker.scale.z = 0.04
            self._set_color(marker, (0.55, 0.55, 0.55), 0.35)
            markers.append(marker)
        return markers

    def _robot_marker(self, idx, name, pose):
        color = COLORS[idx % len(COLORS)]
        yaw = self._yaw_from_pose(pose)

        marker = Marker()
        marker.header.frame_id = self.frame_id
        marker.header.stamp = rospy.Time.now()
        marker.ns = "robots"
        marker.id = idx
        marker.type = Marker.ARROW
        marker.action = Marker.ADD
        marker.pose.position.x = pose.position.x
        marker.pose.position.y = pose.position.y
        marker.pose.position.z = 0.08
        marker.pose.orientation.z = math.sin(yaw / 2.0)
        marker.pose.orientation.w = math.cos(yaw / 2.0)
        marker.scale.x = 0.55
        marker.scale.y = 0.12
        marker.scale.z = 0.12
        self._set_color(marker, color, 1.0)
        return marker

    def _label_marker(self, idx, name, pose):
        color = COLORS[idx % len(COLORS)]
        marker = Marker()
        marker.header.frame_id = self.frame_id
        marker.header.stamp = rospy.Time.now()
        marker.ns = "robot_labels"
        marker.id = idx
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD
        marker.pose.position.x = pose.position.x
        marker.pose.position.y = pose.position.y
        marker.pose.position.z = 0.55
        marker.pose.orientation.w = 1.0
        marker.scale.z = 0.28
        marker.text = name
        self._set_color(marker, color, 1.0)
        return marker

    def _trail_marker(self, idx, name):
        color = COLORS[idx % len(COLORS)]
        marker = Marker()
        marker.header.frame_id = self.frame_id
        marker.header.stamp = rospy.Time.now()
        marker.ns = "robot_trails"
        marker.id = idx
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.scale.x = 0.035
        self._set_color(marker, color, 0.75)
        marker.points = [Point(x=x, y=y, z=0.04) for x, y in self.trails[name]]
        return marker

    def publish(self):
        marker_array = MarkerArray()
        marker_array.markers.append(self._delete_all_marker())
        marker_array.markers.extend(self._obstacle_markers())

        for idx, name in enumerate(self.agent_names):
            pose = self.poses.get(name)
            if pose is None:
                continue
            marker_array.markers.append(self._trail_marker(idx, name))
            marker_array.markers.append(self._robot_marker(idx, name, pose))
            marker_array.markers.append(self._label_marker(idx, name, pose))

        self.publisher.publish(marker_array)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", default="r1,r2,r3")
    parser.add_argument("--frame", default="odom")
    parser.add_argument("--trail-length", type=int, default=80)
    parser.add_argument("--rate", type=float, default=8.0)
    args = parser.parse_args(rospy.myargv()[1:])

    rospy.init_node("multi_agent_overlay", anonymous=True)
    agent_names = [name.strip() for name in args.agents.split(",") if name.strip()]
    overlay = MultiAgentOverlay(agent_names, args.frame, args.trail_length)
    rate = rospy.Rate(args.rate)
    while not rospy.is_shutdown():
        overlay.publish()
        rate.sleep()


if __name__ == "__main__":
    main()
