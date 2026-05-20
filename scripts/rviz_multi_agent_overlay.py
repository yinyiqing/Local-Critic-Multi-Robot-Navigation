#!/usr/bin/env python3
import argparse
import math
from collections import deque

import rospy
from geometry_msgs.msg import Point
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
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


class MultiAgentOverlay:
    def __init__(self, agent_names, frame_id, trail_length, tf_style):
        self.agent_names = agent_names
        self.frame_id = frame_id
        self.tf_style = tf_style
        self.trails = {name: deque(maxlen=trail_length) for name in agent_names}
        self.poses = {}
        self.publisher = rospy.Publisher(
            "/multi_agent_overlay", MarkerArray, queue_size=1
        )
        self.tf_broadcaster = TransformBroadcaster()
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
            last_pose = self.poses.get(name)
            if last_pose is not None:
                jump = math.hypot(
                    pose.position.x - last_pose.position.x,
                    pose.position.y - last_pose.position.y,
                )
                if jump > 1.0:
                    self.trails[name].clear()
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

    def _base_frame(self, name):
        if self.tf_style == "slash":
            return f"{name}/base_link"
        return f"{name}_base_link"

    def _velodyne_frame(self, name):
        if self.tf_style == "slash":
            return f"{name}_velodyne"
        return f"{name}_velodyne"

    def _broadcast_visual_tf(self, name, pose):
        odom_to_base = TransformStamped()
        odom_to_base.header.stamp = rospy.Time.now()
        odom_to_base.header.frame_id = self.frame_id
        odom_to_base.child_frame_id = self._base_frame(name)
        odom_to_base.transform.translation.x = pose.position.x
        odom_to_base.transform.translation.y = pose.position.y
        odom_to_base.transform.translation.z = 0.0
        odom_to_base.transform.rotation = pose.orientation

        base_to_velodyne = TransformStamped()
        base_to_velodyne.header.stamp = odom_to_base.header.stamp
        base_to_velodyne.header.frame_id = self._base_frame(name)
        base_to_velodyne.child_frame_id = self._velodyne_frame(name)
        base_to_velodyne.transform.translation.x = 0.125
        base_to_velodyne.transform.translation.y = 0.0
        base_to_velodyne.transform.translation.z = 0.25
        base_to_velodyne.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform([odom_to_base, base_to_velodyne])

    def publish(self):
        marker_array = MarkerArray()
        marker_array.markers.append(self._delete_all_marker())

        for idx, name in enumerate(self.agent_names):
            pose = self.poses.get(name)
            if pose is None:
                continue
            self._broadcast_visual_tf(name, pose)
            marker_array.markers.append(self._trail_marker(idx, name))
            marker_array.markers.append(self._label_marker(idx, name, pose))

        self.publisher.publish(marker_array)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", default="r1,r2,r3")
    parser.add_argument("--frame", default="odom")
    parser.add_argument("--trail-length", type=int, default=80)
    parser.add_argument("--rate", type=float, default=8.0)
    parser.add_argument("--tf-style", choices=["underscore", "slash"], default="underscore")
    args = parser.parse_args(rospy.myargv()[1:])

    rospy.init_node("multi_agent_overlay", anonymous=True)
    agent_names = [name.strip() for name in args.agents.split(",") if name.strip()]
    overlay = MultiAgentOverlay(agent_names, args.frame, args.trail_length, args.tf_style)
    rate = rospy.Rate(args.rate)
    while not rospy.is_shutdown():
        overlay.publish()
        rate.sleep()


if __name__ == "__main__":
    main()
