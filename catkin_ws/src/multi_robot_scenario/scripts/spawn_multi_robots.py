#!/usr/bin/env python3
import argparse
import os
import time

import rospy
from gazebo_msgs.srv import SpawnModel
from geometry_msgs.msg import Pose
from tf.transformations import quaternion_from_euler


def parse_robot(value):
    parts = value.split(",")
    if len(parts) != 5:
        raise argparse.ArgumentTypeError(
            "robot must use name,x,y,z,yaw format"
        )
    name = parts[0].strip()
    if not name:
        raise argparse.ArgumentTypeError("robot name must not be empty")
    try:
        position = tuple(float(part) for part in parts[1:])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return (name, *position)


def main():
    parser = argparse.ArgumentParser(
        description="Spawn robot models sequentially through Gazebo's service."
    )
    parser.add_argument("robots", nargs="+", type=parse_robot)
    args = parser.parse_args(rospy.myargv()[1:])
    settle_seconds = float(os.environ.get("DRL_MULTI_SPAWN_SETTLE_SECONDS", "2.0"))
    if settle_seconds < 0.0:
        raise ValueError("DRL_MULTI_SPAWN_SETTLE_SECONDS must be non-negative")

    rospy.init_node("sequential_multi_robot_spawner")
    rospy.wait_for_service("/gazebo/spawn_urdf_model")
    spawn_model = rospy.ServiceProxy("/gazebo/spawn_urdf_model", SpawnModel)

    for name, x, y, z, yaw in args.robots:
        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = z
        quaternion = quaternion_from_euler(0.0, 0.0, yaw)
        pose.orientation.x = quaternion[0]
        pose.orientation.y = quaternion[1]
        pose.orientation.z = quaternion[2]
        pose.orientation.w = quaternion[3]
        model_xml = rospy.get_param(f"/robot_description_{name}")
        response = spawn_model(
            model_name=name,
            model_xml=model_xml,
            robot_namespace=f"/{name}",
            initial_pose=pose,
            reference_frame="world",
        )
        if not response.success:
            raise RuntimeError(f"Failed to spawn {name}: {response.status_message}")
        rospy.loginfo("Spawned %s: %s", name, response.status_message)
        # Let model plugins finish before the next synchronous spawn request.
        time.sleep(settle_seconds)

    rospy.loginfo("Sequentially spawned %d robots", len(args.robots))
    rospy.spin()


if __name__ == "__main__":
    main()
